# codex-handoff.md — Codex → Claude 작업 인계 (rolling log)

> **용도:** Codex가 한 작업/판단/이어받을 사항을 Claude에게 전달하는 인계 채널.
> **최신 항목이 맨 위.**
>
> - 상세 연대기 기록은 `history/2026-07-15-codex.md`에 따로 남김.
> - 환경 제약과 repo 지도는 `AGENTS.md` 참고.

---

## 2026-07-15 — Claude 모델별 분리안 검토 + Codex 실험본 기록

### 내가 확인한 것

- Claude handoff는 사용자가 말한 `docs/handoff/claude-handoff.md`가 아니라
  `docs/handoff/claudex-handoff.md`로 존재함. 이름이 의도인지 오타인지 확인 필요.
- 모델별 분리 산출물 확인:
  - `quickstartsmaples/model-preparation/Qwen3/build_qwen3.py`
  - `quickstartsmaples/model-preparation/Llama/build_llama.py`
  - `quickstartsmaples/model-preparation/Gemma4_try/build_gemma_TEMPLATE.py`
- 위 3개 파일은 `python -m compileall -q ...` 문법 검사를 통과함.
- `furiosa-student-kit` git repo는 현재 clean 상태였음.

### Codex 판단

나는 여전히 **최종 학생 키트 구조는 공용 build script 1개 유지**가 더 낫다고 봄.
이유는 다음과 같음.

1. 수업 핵심인 `effective_cpus()`/Ray worker CPU 예산 로직이 Qwen3/Llama/Gemma 파일에
   그대로 복제되어 drift 위험이 생김.
2. 기존 `build_artifact.py`의 핵심 버그였던 `--workers * cpu_per_worker` 총량 미검증이
   모델별 스크립트 3개에도 그대로 복제됨.
3. Qwen3/Llama는 모델 ID와 인증 여부만 다를 뿐, 빌드 로직은 공용 스크립트로 충분히 표현 가능함.
4. Gemma 템플릿은 예외로 둘 수 있음. 프리셋이 없어 학생이 `BucketConfig`를 직접 채우는
   실습이라, 뼈대 파일 자체에는 교육적 의미가 있음.

다만 사용자/Claude 쪽 맥락에는 "원본 안전 > DRY" 결정이 있었음. 따라서 바로 제거하기보다
아래처럼 정리하는 것을 추천.

### 추천 방향

- **권장 최종안:** `_kit/scripts/build_artifact.py` 공용 1개에 Codex 개선점 흡수.
- **Gemma만 예외:** `Gemma4_try/build_gemma_TEMPLATE.py`는 템플릿으로 유지 가능.
- **Qwen3/Llama 독립 스크립트:** 지금은 실험/옵션으로 두되, 최종 배포 전에는 README와 함께
  공용 스크립트 방식으로 되돌릴지 사용자에게 확인.
- **반드시 고칠 버그:** 모델별 스크립트를 유지한다면 세 파일 모두 worker-aware CPU 계산으로 수정 필요.

### Codex가 만든 별도 실험본

원본을 건드리지 않기 위해 `codex_` 접두사 파일을 만들었음.

- `docs/codereview/codex_2026-07-15-claude-codereview.md`
- `quickstartsmaples/model-preparation/_kit/scripts/codex_build_artifact.py`
- `quickstartsmaples/model-preparation/_kit/scripts/codex_verify_artifact.py`

검증:

- `codex_build_artifact.py`, `codex_verify_artifact.py` compileall 통과.
- 두 스크립트 `--help` 실행 확인.
- `codex_build_artifact.py --model dummy --workers 999 --dry-run`이 ArtifactBuilder 생성 전에
  CPU 총량 초과로 실패하는 것 확인.

### 이어받을 때 주의

- `quickstartsmaples/`와 `furiosa-student-kit/quickstartsmaples/`는 별도 사본임.
  현재 모델별 스크립트와 Codex 실험본은 `/root/works/quickstartsmaples/` 쪽에서 확인됨.
- 빌드 산출물(`*-artifact/`, `*.safetensors`, `binary_bundle.zip`)은 커밋 금지.
- `Gemma4_try/build_gemma_TEMPLATE.py`는 의도적 미완성. 완성본으로 바꾸기 전 사용자 확인 필요.
