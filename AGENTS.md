# AGENTS.md — 이 워크스페이스에서 작업하는 모든 에이전트/도구를 위한 안내

> 이 파일은 특정 도구 전용이 아닙니다. Claude Code, Copilot, Cursor 등 **어떤 AI
> 에이전트나 사람**이든 이 워크스페이스에서 작업을 이어받을 때 먼저 읽으세요.
> (Claude Code에는 별도 메모리도 있지만 그건 Claude 전용이라, 도구 중립 내용은 여기 둡니다.)

---

## ⚠️ 가장 먼저 알아야 할 것: 이 환경은 보ㅇ이는 것과 다릅니다

이 컨테이너/pod는 128코어처럼 보이지만 **실제로는 그렇지 않습니다.**

```bash
nproc                                    # 128 이라고 나옴 → 호스트 코어. 믿지 마세요.
awk '{printf "%.0f\n",$1/$2}' /sys/fs/cgroup/cpu.max   # 실제 실효 CPU (측정 시점 15)
df -h /dev/shm                           # 64MB 뿐 (ray/torch 공유메모리)
```

**측정 시점(2026-07-15) 값: 실효 CPU 15개, `/dev/shm` 64MB, RAM ~1TB.**
이 값은 pod마다/시간에 따라 바뀔 수 있으니 **숫자를 외우지 말고 매번 측정**하세요:

```bash
bash quickstartsmaples/model-preparation/_kit/scripts/check_resources.sh
```

### 왜 중요한가 (실제로 5시간 날린 사례)
`nproc=128`을 믿고 병렬 빌드 워커를 128코어 기준으로 잡았다가, 실제 15코어에서
빌드가 파이프라인당 20분(총 14시간 예상)으로 정체하거나 아예 멈췄습니다.
전체 사고 기록: [postmortem](quickstartsmaples/model-preparation/_kit/02_POSTMORTEM.md).

**규칙 3개 (모든 병렬/빌드 작업 공통):**
1. `nproc` 대신 **cgroup 실효 CPU를 측정**한다.
2. 워커 수 × 워커당 CPU ≤ 실효 CPU. `/dev/shm`이 작으면 워커는 1개.
3. 런타임 시작 로그의 **`WARNING`을 끝까지 읽는다** (`Detecting docker specified CPUs`,
   `object store is using /tmp/ray instead of /dev/shm`).

---

## 이 워크스페이스가 하는 일

Furiosa NPU용 LLM **아티팩트 빌드** 실습 자료를 만들고, 학생 배포용 키트로 정리합니다.

### 핵심 위치
| 무엇 | 경로 |
|---|---|
| 실습 인덱스 | `quickstartsmaples/model-preparation/README.md` |
| 공용 가이드·스크립트 | `quickstartsmaples/model-preparation/_kit/` |
| 빌드 스크립트(자원 자동측정) | `_kit/scripts/build_artifact.py` |
| 자원 확인 | `_kit/scripts/check_resources.sh` |
| 검증 | `_kit/scripts/verify_artifact.py` |
| 완성 레퍼런스 | `quickstartsmaples/model-preparation/qwen2.5-0.5b/` |

### 아티팩트 빌드 표준 절차
```bash
cd quickstartsmaples/model-preparation/_kit/scripts
bash check_resources.sh                                              # 0. 자원 확인
python build_artifact.py --model <ID> [--fix-append] --dry-run       # 1. 검증(컴파일 X)
python build_artifact.py --model <ID> [--fix-append] -o ./out        # 2. 빌드
python verify_artifact.py --artifact ./out 2>&1 | tee verify.log     # 3. 확인
```
`--fix-append`는 프리셋에 append_buckets가 없는 모델(Qwen2.5-0.5B)에만. dry-run에서
`append_buckets`가 0이면 필요, 0보다 크면 불필요.

---

## git 저장소 지도 (헷갈리지 마세요)

`/root/works` **자체는 git repo가 아닙니다.** 아래 3곳만 독립된 repo입니다:

| 경로 | 리모트 | 용도 |
|---|---|---|
| `furiosa-student-kit/` | github: futurianh1k/furiosa-student-kit | **학생 배포용** (여기에 실습 자료 사본) |
| `furiosa-repo/furiosa-apps/` | (furiosa 공식) | 참고용 |
| `warboy/warboy-sdk/` | (furiosa 공식) | 참고용 |

⚠ **빌드 산출물을 커밋하지 마세요.** `*.safetensors`(950MB), `*-artifact/`,
`binary_bundle.zip` 등은 `.gitignore`에 있습니다. GitHub 100MB 제한에 걸립니다.
큰 파일은 LFS가 아니라 **gitignore로 제외**합니다(학생이 재생성하는 산출물이므로).

---

## 에이전트 간 협업 규칙 (Claude ↔ Codex ↔ 사람)

여러 에이전트가 이 워크스페이스를 공유합니다. 다음 두 규칙을 지키세요.

1. **서로 전달할 내역은 `docs/handoff/`에 둔다.** 상대(동료 에이전트)에게 넘길 작업·수정
   내역, 인계 사항, 이어서 할 일을 여기에 append 합니다. Claude↔Codex 공용 인계 채널입니다.
   - Claude→Codex: `docs/handoff/claudex-handoff.md` (최신 항목이 위)
   - Codex→Claude: `docs/handoff/` 안 자기 파일에 남기고, 상대는 그걸 읽고 이어받음
2. **각자 자기 작업 내역은 `history/`에 기록한다.** 개인 작업 로그(무엇을 왜 했는지)는
   `history/<날짜>-<도구>.md` 형식으로 남깁니다. 상대 전달용이 아니라 **자기 기록용**입니다.

> **handoff = 상대에게 넘기는 것(curated·actionable), history = 내 기록(상세·연대기).**
> 이 AGENTS.md에는 위처럼 **안정적인 규칙만 얇게** 두고, 자주 바뀌는 진행 상태·작업 내역은
> `docs/handoff/`·`history/`에 둡니다(이 파일 비대화 방지).

---

## 현재 진행 상태 / 남은 일 (2026-07-15 기준)

> ⚠ 최신 진행 상태는 위 규칙에 따라 **`docs/handoff/claudex-handoff.md`** 를 보세요.
> 아래는 초기 스냅샷이며 갱신되지 않을 수 있습니다.

**끝난 것**
- 학생 키트 완성 + `model-preparation/`에 통합, 스크립트 전부 검증.
- `furiosa-student-kit` repo 정리: 실수로 커밋된 950MB safetensors를 히스토리에서
  제거(`git rm --cached` + `commit --amend` + gc). `.git` 757MB→256KB. **push 준비됨.**

**남은 것**
1. `cd furiosa-student-kit && git push origin main` (미실행, `--force` 불필요 — 원격은 비어있음).
2. VS Code 환경 정비.
3. `furiosa-student-kit/quickstartsmaples/`와 `/root/works/quickstartsmaples/`는
   **별도 사본** → 동기화 여부 결정 필요.
