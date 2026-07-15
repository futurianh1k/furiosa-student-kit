# Furiosa 아티팩트 빌드 실습 가이드

> 이 가이드는 실제 삽질에서 나왔습니다. 조교가 이 실습 환경에서 아티팩트 하나를
> 재빌드하다가 **5시간을 태우고 두 번 실패**한 뒤 원인을 찾았습니다. 여러분은 그
> 실수를 반복하지 않도록, 그 결론만 먼저 받아 갑니다. 왜 그렇게 됐는지 전체 이야기는
> [02_POSTMORTEM.md](02_POSTMORTEM.md)에 있습니다.

---

## 0. 딱 세 줄 요약

1. **`nproc`를 믿지 마세요.** 여러분의 pod는 128코어처럼 보이지만 실제로는 **15코어**입니다.
2. **빌드 전에 `check_resources.sh`를 실행**해서 진짜 자원을 확인하세요.
3. **런타임이 시작할 때 뱉는 `WARNING`을 끝까지 읽으세요.** 답이 거기 다 있습니다.

---

## 1. 이 실습에서 하는 일

Furiosa NPU에서 LLM을 돌리려면 모델을 NPU용으로 **컴파일한 "아티팩트"**가 필요합니다.
Furiosa가 허브에 미리 만들어 올려둔 아티팩트도 있지만, 어떤 모델은 그 아티팩트가
**불완전하게** 빌드되어 있습니다. 이 실습은 그걸 **직접 다시 빌드**해서 고칩니다.

구체적으로, `Qwen2.5-0.5B-Instruct`의 기성 아티팩트로 추론을 돌리면 이런 경고가 뜹니다:

```
WARN ... No extend buckets ... Chunked prefill will be disabled ...
WARN ... Disabling prefix caching ...
```

이건 **`append_buckets`(=extend bucket)가 빠져서** 런타임이 두 최적화 기능
(chunked prefill, prefix caching)을 자동으로 꺼버린 것입니다. 서빙에서 공통 프롬프트
접두사를 반복하거나 긴 입력을 다룰 때 성능이 크게 나빠집니다.

여러분의 목표: **`append_buckets`를 채워 아티팩트를 재빌드하고, 경고가 사라지는지 확인.**

---

## 2. 환경의 함정 (이게 이 실습의 진짜 교훈)

### 함정 ①: `nproc`는 거짓말을 합니다

```bash
$ nproc
128            # ← 호스트(물리 서버)의 코어. 여러분 것이 아님!
$ awk '{printf "%.0f\n", $1/$2}' /sys/fs/cgroup/cpu.max
15             # ← cgroup 이 정한 여러분 pod 의 실제 CPU
```

컨테이너/pod는 cgroup으로 CPU가 제한됩니다. `nproc`나 파이썬 `os.cpu_count()`는
그 제한을 무시하고 **호스트 코어 수**를 보고할 수 있습니다. 이걸 믿고 "128코어니까
워커를 잔뜩!" 하면, 있지도 않은 코어를 요청하다 빌드가 **20배 느려지거나 멈춥니다.**

### 함정 ②: `/dev/shm`이 64MB뿐입니다

빌드 도구(ray)는 작업자들끼리 데이터를 주고받을 때 공유메모리(`/dev/shm`)를 씁니다.
그런데 여기는 64MB밖에 없어서, ray가 그걸 **디스크로 우회**합니다. 시작 로그에
이렇게 대놓고 경고가 나옵니다:

```
WARNING: The object store is using /tmp/ray instead of /dev/shm because
/dev/shm has only 67108864 bytes available. This will harm performance!
```

**교훈: 워커를 많이 만들수록 이 디스크 우회 트래픽이 늘어 더 느려집니다.
→ 워커는 1개, 워커당 CPU는 크게.**

---

## 3. 올바른 순서 (이대로만 하세요)

### Step 0. 자원 확인 — **항상 먼저**
```bash
cd furiosa-student-kit/scripts
bash check_resources.sh
```
실효 CPU / shm / RAM과, 이 pod에 맞는 빌드 권고값을 출력합니다.

### Step 1. dry-run — 컴파일 전에 버킷 검증
```bash
python build_artifact.py --model Qwen/Qwen2.5-0.5B-Instruct --fix-append --dry-run
```
- `append_buckets : 6` 처럼 **0이 아니어야** 합니다 (0이면 prefix caching이 꺼집니다).
- `[자원] 실효 CPU=15 ... → 워커당 CPU=14` 로 **자동 측정**되는지 확인하세요.
- 에러 없이 `[dry-run] 검증 통과`가 나오면 다음 단계로.

### Step 2. 실제 빌드
```bash
python build_artifact.py --model Qwen/Qwen2.5-0.5B-Instruct --fix-append -o ./qwen25-artifact
```
- 워커 CPU는 **자동으로 여러분 pod에 맞춰집니다** (직접 숫자를 넣지 마세요).
- 정상이면 파이프라인당 **7~20초**, 전체 **10여 분**이면 끝납니다.
- 만약 진행이 `0/N`에서 안 움직이거나 파이프라인당 수 분씩 걸리면 → **뭔가 잘못된 것.**
  Step 0의 자원값과 워커 설정을 다시 보세요. (자세히: 02_POSTMORTEM.md)

### Step 3. 검증
```bash
python verify_artifact.py --artifact ./qwen25-artifact 2>&1 | tee verify.log
```
성공 기준:
- 출력이 정상적으로 나온다 (예: "...Paris.")
- 로그에 `No extend buckets` / `Disabling prefix caching`이 **없다**
- 로그에 `is_prefix_cache_enabled: true`가 **있다**

---

## 4. 다른 모델은? (Qwen3 / Llama / Gemma)

**`--fix-append`는 Qwen2.5-0.5B 전용입니다.** 이 모델만 프리셋에 `append_buckets`가
빠져 있기 때문입니다. Llama·Qwen3 등 다른 모델은 프리셋에 이미 들어 있어서, 그냥:

```bash
python build_artifact.py --model meta-llama/Llama-3.1-8B-Instruct -o ./llama-artifact
```
처럼 `--fix-append` **없이** 빌드하면 됩니다. dry-run에서 `append_buckets`가 이미
0보다 크면 손댈 필요가 없다는 뜻입니다.

> 큰 모델(8B, 32B…)은 파이프라인 수가 많아 빌드가 더 오래 걸립니다. 15코어 pod에서는
> 인내심이 필요합니다. 그래도 `0/N`에서 멈추면 그건 느린 게 아니라 **틀린** 것입니다.

---

## 5. 자주 겪는 증상과 원인

| 증상 | 원인 | 해결 |
|---|---|---|
| 빌드가 `0/N`에서 안 움직임 | 워커당 CPU > 실효 CPU → ray가 배치 불가 | 워커당 CPU를 실효 CPU 이하로 (스크립트가 자동으로 함) |
| 파이프라인당 수 분~수십 분 | 워커 과다 + shm 디스크 우회 | 워커 1개로 |
| `Partial bucket configuration is not allowed` | 버킷 4종 중 일부만 채움 | 4종을 다 채우거나 다 비우기 |
| `24 > 15` 류로 멈춤 | `nproc`(128) 믿고 큰 값 지정 | `check_resources.sh` 값 사용 |
| `append_buckets: 0` | 프리셋에 append 없음(Qwen2.5-0.5B) | `--fix-append` 사용 |

---

## 6. 파일 안내

```
furiosa-student-kit/
├── 01_GUIDE.md          ← 지금 이 문서
├── 02_POSTMORTEM.md     ← 왜 이 가이드가 존재하는지 (실패의 전체 기록)
├── CHECKLIST.md         ← 한 장짜리 체크리스트 (실습 중 곁에 두세요)
└── scripts/
    ├── check_resources.sh   ← Step 0: 빌드 전 자원 확인
    ├── build_artifact.py    ← Step 1~2: dry-run & 빌드 (자원 자동 측정)
    └── verify_artifact.py   ← Step 3: 경고가 사라졌는지 검증
```

막히면 02_POSTMORTEM.md의 "빠른 진단 체크리스트"를 먼저 보세요.
거기에 조교가 5시간 헤맨 끝에 정리한, 바로 통하는 명령어들이 있습니다.
