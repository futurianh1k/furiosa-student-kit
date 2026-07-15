# Furiosa 아티팩트 빌드 Post-mortem: `nproc`를 믿고 14시간을 태울 뻔한 이야기

> **형식**: 사후 분석(post-mortem) 겸 기술 백서
> **작성일**: 2026-07-14
> **대상 독자**: 이 워크스페이스(또는 유사한 컨테이너 환경)에서 `furiosa-llm` 아티팩트를
> 직접 빌드하려는 사람, 그리고 다음 세션의 나 자신
> **한 줄 요약**: `ArtifactBuilder`의 워커 개수를 세 번 바꾼 것은 대부분 헛수고였고,
> 진짜 원인은 컨테이너의 **cgroup CPU 15개 제한**과 **64MB `/dev/shm`**이라는
> *환경 사실*을 처음부터 확인하지 않은 것이었다.

---

## 1. 배경 (What we were doing)

`furiosa-ai/Qwen2.5-0.5B-Instruct`의 기성(pre-built) 아티팩트로 단발 추론을 돌리면
로그에 다음 두 경고가 떴다.

```
WARN ... No extend buckets with kv_cache_size > 0 found in the artifact.
     Chunked prefill will be disabled ...
WARN ... Prefix caching is enabled but no extend buckets are available.
     Disabling prefix caching ...
```

원인은 명확했다. `furiosa_llm/artifact/presets.py`의 `QWEN_2_5_0D5B_PRESET`에
**`append_buckets`(런타임 용어로 "extend bucket")가 누락**되어 있었다. 다른 프리셋
(Llama 3.1/3.3, EXAONE, Qwen3)에는 모두 있다. 그래서 런타임이 chunked prefill과
prefix caching을 자동으로 껐다.

해결책 자체는 단순했다 — `append_buckets`를 채워서 아티팩트를 **직접 재빌드**하면 된다.
문제는 그 "직접 재빌드"가 세 번의 시도와 여러 시간을 잡아먹었다는 것이다.

---

## 2. 타임라인 (What happened)

세 번의 빌드 시도. 모두 같은 모델, 같은 코드, 오직 **버킷 수와 워커 설정만** 달랐다.

| | 워커 설정 | append 버킷 | 결과 | 관측된 속도 |
|---|---|---|---|---|
| **run 1** | 파이프라인 42×1CPU, 컴파일 32×4CPU | 34개 (파이프라인 43) | 5시간 22분 후 **16/43**에서 강제 종료 | **1234 s/it** (파이프라인당 ~20분), 완료 예상 14.5시간 |
| **run 2** | 파이프라인 5×24CPU, 컴파일 4×32CPU | 34개 (파이프라인 43) | 7분간 **0/43**에서 멈춤, 종료 | 액터 배치 자체가 안 됨 |
| **run 3** | 파이프라인 1×12CPU, 컴파일 1×12CPU | **6개** (파이프라인 14) | **성공**, 총 ~13분 | **7~21 s/it** |

run 1과 run 2에서 공통적으로 관측된 이상 징후:

- **머신이 놀고 있었다.** `nproc`는 128인데 load average는 4에서 꼼짝하지 않았다.
- **워커가 자고 있었다.** ray 워커들이 `state=S, wchan=ep_poll`(할 일 대기) 또는
  `pipe_read`(객체 전달 대기) 상태였다. 계산도 디스크도 아닌, 순수 대기.
- 파이프라인 1개의 *실제* 계산량은 초 단위였다 (`ATen graph generation took 2s`).
  그런데 파이프라인당 벽시계 시간은 20분이었다. **19분 58초가 낭비**되고 있었다.

---

## 3. 근본 원인 (Root cause)

### 3.1 진짜 원인: 컨테이너 자원을 확인하지 않았다

```
$ nproc
128
$ cat /sys/fs/cgroup/cpu.max
1500000 100000        # quota / period = 15.0 CPUs
$ df -h /dev/shm
shm  64M  0  64M  0%  /dev/shm      # 게다가 write-protected, remount 불가
```

`nproc`가 보고한 **128은 호스트의 물리 코어**이고, 이 컨테이너가 cgroup으로 실제
쓸 수 있는 것은 **CPU 15개**였다. 여기에 ray 오브젝트 스토어(워커 간 객체 전달)가
쓰는 `/dev/shm`이 **64MB뿐**이라, ray는 이를 디스크(`/tmp`)로 폴백했다.

이 두 사실이 세 번의 시도를 전부 설명한다:

- **run 1** (워커당 1 CPU): 1 ≤ 15이라 42개 워커가 배치는 됐지만, 15코어를 두고
  42개가 경합 + 큰 그래프 객체를 디스크 경유로 주고받으며 파이프라인당 20분.
- **run 2** (워커당 24 CPU): **24 > 15**. ray가 15-CPU 클러스터에 24-CPU 액터를
  **단 하나도 배치할 수 없어** 0/43에서 영구 정지. (내 "수정"이 오히려 악화시켰다.)
- **run 3** (워커당 12 CPU, 워커 1개): 12 ≤ 15이라 배치 가능 + 워커가 1개라
  디스크 IPC 최소화 → 파이프라인당 7~21초. 정상.

### 3.2 결정적 단서는 처음부터 로그에 있었다

ray는 **run이 시작될 때마다** 두 경고를 직접 출력하고 있었다:

```
WARNING utils.py -- Detecting docker specified CPUs. ... Please ensure that Ray
        has enough CPUs allocated. ...
WARNING services.py -- WARNING: The object store is using /tmp/ray instead of
        /dev/shm because /dev/shm has only 67108864 bytes available.
        This will harm performance! ...
```

두 경고 모두 `67108864 bytes`(=64MB)와 `docker specified CPUs`를 명시하고 있었다.
**나는 초반에 이 로그를 끝까지 읽지 않았다.** 진행 막대(`16/43`)와 반복되는 INFO 줄만
보고 "느리다"고만 판단했지, 시작부의 WARNING을 놓쳤다.

---

## 4. 질문에 대한 답: "docs를 정독했다면 오판을 막았을까?"

**대체로 아니다.** 이유는 세 겹이다.

1. **docs는 환경 사실을 알려주지 않는다.** 이 컨테이너가 15 CPU / 64MB shm이라는 건
   Furiosa 문서 어디에도 없다 — 있을 수도 없다. 이건 배포 환경의 속성이지 라이브러리의
   속성이 아니다. 오판의 **결정적** 원인이 바로 이 환경 사실이었으므로, docs로는 못 막았다.

2. **워커당 CPU 권장값(빌더 24 / 컴파일 32)은 docs에 없었다.** 확인해보니 그 값은
   소스 코드의 `@ray.remote(num_cpus=24)` 데코레이터와 `# OMP_NUM_THREADS ...` 주석에만
   있었다. 즉 이 건에 한해서는 **docs보다 소스가 더 정확**했다. docs는 워커/CPU 비율에
   대한 구체적 지침을 주지 않는다 (`num_pipeline_builder_workers`를 키우면 "메모리가
   훨씬 많이 필요하다"는 한 줄이 전부다).

3. **docs가 도움이 됐을 지점도 있긴 하다.** "워커를 늘리면 메모리를 많이 쓴다"는 서술은,
   워커가 *무거운 멀티스레드 단위*라는 사실을 암시한다. 이걸 먼저 읽었다면 "워커 수를
   최대로, 워커당 CPU를 최소로"라는 run 1의 잘못된 직관을 조금 더 일찍 의심했을 수는 있다.
   하지만 그건 부차적이다.

**결론**: 이건 *문서 독해 실패*가 아니라 *환경 관측 실패*였다. 고쳐야 할 습관은
"docs를 더 읽자"가 아니라 **"코드를 돌리기 전에 실제 자원을 측정하자"**와
**"런타임이 시작할 때 뱉는 WARNING을 끝까지 읽자"**이다.

---

## 5. 교훈 (Lessons learned)

### L1. 컨테이너에서 `nproc`를 믿지 마라 — cgroup을 봐라
```bash
# 실제 가용 CPU (cgroup v2)
awk '{ printf "%.1f CPUs\n", $1/$2 }' /sys/fs/cgroup/cpu.max
# /dev/shm 크기 (ray/plasma·torch 공유메모리 성능에 직결)
df -h /dev/shm
```
`nproc`/`multiprocessing.cpu_count()`는 컨테이너에서 **호스트 코어를 보고**할 수 있다.
병렬도 관련 설정은 반드시 cgroup 실효값에 맞춰라.

### L2. 무거운 작업을 걸기 전, 시작 로그의 WARNING을 끝까지 읽어라
ray/torch/furiosa 런타임은 초기화 시점에 자원 오인·성능 저하 경고를 **먼저** 뱉는다.
진행 막대를 보기 전에 시작부 30줄을 읽었다면 5시간을 아꼈다.

### L3. `ArtifactBuilder`의 워커 파라미터는 "개수"가 아니라 "코어 예산 분배"다
- `num_*_workers` × `num_cpu_per_*_worker` = 점유 코어. 이 곱이 **실효 CPU 이하**여야 한다.
- `num_cpu_per_*_worker`는 ray `num_cpus`를 거쳐 `OMP_NUM_THREADS`로 흘러가
  **워커 내부 스레드 풀 크기**를 정한다. 1로 깎으면 워커 내부 병렬성이 죽는다.
- **워커당 CPU가 실효 CPU 총량을 넘으면 ray가 액터를 아예 배치하지 못한다** (run 2).

### L4. `/dev/shm`이 작으면 워커는 적게 써라
오브젝트 스토어가 디스크로 폴백되면 워커 간 객체 전달이 병목이 된다. 이럴 땐 워커를
늘리는 것이 오히려 독이다. **워커 적게 / 워커당 CPU 크게**가 유리하다 (run 3).

### L5. 작은 모델에 34개 버킷은 과하다 — 필요한 조합만
`append_buckets`는 전조합(attn × input)을 넣을 필요가 없다. 대표 조합 몇 개면 충분하고,
파이프라인 수가 줄면 빌드 시간과 디스크 IPC 부담이 함께 준다 (43 → 14).

### L6. 오판을 인정하고 측정으로 되돌아와라
run 1의 "워커 설정이 원인"이라는 내 진단은 부분적으로만 맞았다(설정은 틀렸지만 그게
지배적 병목은 아니었다). run 2가 더 나빠진 뒤에야 `cgroup`과 `/dev/shm`을 측정했다.
**추정보다 측정이 먼저**였어야 했다.

---

## 6. 이 환경에서 통하는 설정 (Reference config)

**환경**: cgroup CPU 15개, `/dev/shm` 64MB(확장 불가), RAM ~1TB.

```python
# 15-CPU 컨테이너에 맞춘 값. 핵심: 워커당 CPU ≤ 15, 워커는 적게(디스크 IPC 최소화).
builder.build(
    "./qwen2.5-0.5b-artifact",
    num_pipeline_builder_workers=1,
    num_cpu_per_pipeline_build_worker=12,   # 1 × 12 ≤ 15
    num_compile_workers=1,
    num_cpu_per_compile_worker=12,          # 1 × 12 ≤ 15
)
```
- 파이프라인 빌드와 컴파일은 **순차 실행**이라 각각 12를 잡아도 피크가 겹치지 않는다.
- 결과: 파이프라인당 7~21초, 총 빌드 ~13분 (run 1의 14.5시간 예상 대비).

일반화하면:
- `num_cpu_per_*_worker` ≤ (cgroup 실효 CPU)
- `num_*_workers × num_cpu_per_*_worker` ≲ (cgroup 실효 CPU)
- `/dev/shm`이 작다 → `num_*_workers`는 1~2로 낮게.

---

## 7. 검증 (Verification)

재빌드한 아티팩트로 동일 추론을 돌려 목표를 확인했다.

| 항목 | 기성 아티팩트 | 재빌드 |
|---|---|---|
| `No extend buckets` 경고 | 있음 | **0건** |
| `Chunked prefill will be disabled` | 있음 | **0건** |
| `Disabling prefix caching` | 있음 | **0건** |
| `is_prefix_cache_enabled` | `false` | **`true`** |
| 추론 출력 | "...Paris." | "...Paris." (동일) |

경고가 사라진 것에 그치지 않고 KVCacheManager 로그에 `is_prefix_cache_enabled: true`가
찍혀, prefix caching이 **실제로 활성화**됐음을 확인했다.

---

## 8. 부록: 빠른 진단 체크리스트

새 환경에서 furiosa 아티팩트(또는 임의의 ray/멀티프로세스 빌드)를 걸기 전:

```bash
# 1. 실효 CPU (호스트 코어가 아니라 cgroup 값)
awk '{printf "effective CPUs: %.1f\n", $1/$2}' /sys/fs/cgroup/cpu.max 2>/dev/null || echo "cgroup v1? check cpu.cfs_quota_us/cfs_period_us"
# 2. 공유메모리 (ray object store 성능)
df -h /dev/shm
# 3. 메모리 여유 (워커 수를 늘릴 때 제약)
free -g | awk '/Mem:/{print "RAM avail: "$7" GiB"}'
```
그리고 **빌드 시작 로그의 첫 30줄에서 `WARNING`을 찾아 읽어라.** 특히:
- `Detecting docker specified CPUs`
- `object store is using /tmp/ray instead of /dev/shm`

이 둘이 보이면, 위 설정 원칙(워커당 CPU ≤ 실효 CPU, 워커는 적게)을 적용하라.
