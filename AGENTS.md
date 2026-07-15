# AGENTS.md — 이 저장소에서 작업하는 에이전트/사람을 위한 안내

> Claude Code, Copilot, Cursor 등 **어떤 AI 에이전트나 사람**이든 이 저장소에서
> 작업하거나 실습을 도울 때 먼저 읽으세요. 특정 도구 전용이 아닙니다.

이 저장소는 **Furiosa NPU Pod에서 LLM 아티팩트를 빌드하는 실습 키트**입니다.

---

## ⚠️ 가장 먼저: 이 Pod는 보이는 것과 다릅니다

실습 pod는 128코어처럼 보이지만 **실제 쓸 수 있는 CPU는 그보다 훨씬 적습니다.**

```bash
nproc                                    # 128 → 호스트 코어. 믿지 마세요.
awk '{printf "%.0f\n",$1/$2}' /sys/fs/cgroup/cpu.max   # 실제 실효 CPU (예: 15)
df -h /dev/shm                           # 공유메모리 (예: 64MB)
```

**이 값은 pod마다 다를 수 있으니 외우지 말고 매번 측정하세요:**
```bash
bash quickstartsmaples/model-preparation/_kit/scripts/check_resources.sh
```

### 왜 중요한가
`nproc`를 믿고 빌드 병렬도를 잘못 잡으면 빌드가 **수십 배 느려지거나 아예 멈춥니다.**
(실제로 그렇게 5시간을 날린 기록:
[postmortem](quickstartsmaples/model-preparation/_kit/02_POSTMORTEM.md))

**규칙 3개 (모든 빌드 공통):**
1. `nproc` 대신 **cgroup 실효 CPU를 측정**한다.
2. 워커 수 × 워커당 CPU ≤ 실효 CPU. `/dev/shm`이 작으면 워커는 1개.
3. 런타임 시작 로그의 **`WARNING`을 끝까지 읽는다.**

---

## 어디서부터 시작하나

| 순서 | 파일 |
|---|---|
| 1 | [실습 인덱스](quickstartsmaples/model-preparation/README.md) |
| 2 | [메인 가이드](quickstartsmaples/model-preparation/_kit/01_GUIDE.md) |
| 3 | [체크리스트](quickstartsmaples/model-preparation/_kit/CHECKLIST.md) |
| 참고 | [postmortem (실패 기록)](quickstartsmaples/model-preparation/_kit/02_POSTMORTEM.md) |

### 빌드 표준 절차
```bash
cd quickstartsmaples/model-preparation/_kit/scripts
bash check_resources.sh                                          # 0. 자원 확인
python build_artifact.py --model <ID> [--fix-append] --dry-run   # 1. 검증(컴파일 X)
python build_artifact.py --model <ID> [--fix-append] -o ./out    # 2. 빌드
python verify_artifact.py --artifact ./out 2>&1 | tee verify.log # 3. 확인
```
`--fix-append`는 프리셋에 append_buckets가 빠진 모델(Qwen2.5-0.5B)에만. dry-run에서
`append_buckets`가 0이면 필요, 0보다 크면 불필요합니다.

---

## 기여/작업 시 주의

- **빌드 산출물을 커밋하지 마세요.** `*.safetensors`(약 950MB), `*-artifact/`,
  `binary_bundle.zip` 등은 `.gitignore`에 있습니다. GitHub 100MB 제한에 걸립니다.
  이 큰 파일들은 **학생이 직접 빌드해 재생성**하는 것이라 버전관리 대상이 아닙니다
  (그래서 Git LFS도 쓰지 않습니다).
- 실습 자료를 수정하면 `_kit/scripts/`의 스크립트가 여전히 동작하는지
  `--dry-run`으로 먼저 확인하세요.
