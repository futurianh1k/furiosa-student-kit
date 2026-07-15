# claudex-handoff.md — Claude → Codex 작업 인계 (rolling log)

> **용도:** Claude가 한 작업/수정 내역을 동료 Codex에게 전달하는 인계 채널.
> **최신 항목이 맨 위.** 새 작업을 하면 이 파일 위쪽에 항목을 추가한다.
>
> - 협업 규칙: `AGENTS.md` → "에이전트 간 협업 규칙" 참고.
> - 환경 제약(nproc≠실효CPU=15, /dev/shm 64MB), git repo 지도: `AGENTS.md`.
> - 내(Claude) 개인 상세 기록은 `history/`에 별도로 있음(전달용 아님).

---

## 2026-07-15 — 모델별 빌드 스크립트 분리 + 협업 파일 규칙 수립

### 결정 (사용자 지시)
- 원본 `_kit/scripts/build_artifact.py`는 **동결**. Qwen2.5-0.5B 검증 아티팩트를 만든
  스크립트라 "잘 굴러가던 건 건드리지 말자".
- 나머지 모델은 **각 폴더에 독립 실행본**을 새로 만든다.

### 만든/바꾼 것 (`/root/works/quickstartsmaples/model-preparation/` 아래)
| 폴더 | 새 파일 | 성격 |
|---|---|---|
| `Qwen3/` | `build_qwen3.py` | 프리셋 완비 → 모델 ID 박은 완성 실행본. `--fix-append` 없음 |
| `Llama/` | `build_llama.py` | 완성본 + HF 토큰 미검출 시 경고(gated) |
| `Gemma4_try/` | `build_gemma_TEMPLATE.py` | **빈 뼈대.** `GEMMA_*` 버킷 4종 미완 → 안 채우면 의도적 `SystemExit`. "try/도전"이라 정답 미제공 |

- 세 파일 모두 `effective_cpus()`(cgroup 실효 CPU) 코어를 **자체 포함** → 폴더별 자립 실행.
- 원본 `build_artifact.py`/`verify_artifact.py`/`check_resources.sh`는 **그대로**.
- README 갱신: `Qwen3/`, `Llama/`, `Gemma4_try/`, 상위 `model-preparation/README.md`.

### 검증 상태
- 신규 3파일 `py_compile` 통과. **`furiosa_llm` 실제 dry-run 실행은 미실시**(문법만 확인).

### Codex가 이어받을 수 있는 것
1. **사본 동기화:** 신규 스크립트는 `/root/works/quickstartsmaples/`에만 있음.
   `furiosa-student-kit/quickstartsmaples/`는 **별도 사본** → 동기화 + 커밋/푸시 필요할 수 있음.
   (푸시 대상 repo는 `furiosa-student-kit`만. 산출물 `*.safetensors`/`*-artifact/` 커밋 금지.)
2. **dry-run 실측:** pod에서 `build_qwen3.py --dry-run`, `build_llama.py --dry-run` 실행해
   `append_buckets>0`·파이프라인 수 확인.

### ⚠ 주의
- `Gemma4_try/build_gemma_TEMPLATE.py`는 **의도적 미완성**. 버킷을 채워 "완성"하면 실습
  취지가 깨짐 — 손대려면 사용자 확인.
- 빌드 워커는 항상 `check_resources.sh`로 실효 CPU 먼저 측정(nproc 믿지 말 것).
