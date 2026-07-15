# codex-handoff.md — Codex → Claude 작업 인계 (rolling log)

> **용도:** Codex가 한 작업/판단/이어받을 사항을 Claude에게 전달하는 인계 채널.
> **최신 항목이 맨 위.**
>
> - 상세 연대기 기록은 `history/2026-07-15-codex.md`에 따로 남김.
> - 환경 제약과 repo 지도는 `AGENTS.md` 참고.

---

## 2026-07-15 — Qwen3-VL 8B custom generator registry 가능성 검토

### 내가 확인한 것

- Furiosa 문서 기준 현재 권장 모델 준비 경로는 legacy `ArtifactBuilder`보다 FXB/`fxb build`.
- FXB는 architecture fingerprint 단위로 엄격히 매칭된다. `hidden_size`, attention head 수, sliding window,
  quantization format 같은 kernel generation 관련 config가 다르면 별도 bundle/registry entry가 필요하다.
- Furiosa supported models 문서에는 `Qwen3VLForConditionalGeneration` architecture와 Text/Image modality가
  supported로 올라와 있지만, 검증 예시는 `Qwen/Qwen3-VL-32B-Instruct`,
  `Qwen/Qwen3-VL-2B-Instruct-FP8`이고 `Qwen/Qwen3-VL-8B-Instruct` exact validation은 보이지 않는다.
- `fxb` CLI에는 `build/download/add/check/cache/show/inspect`만 있고, 사용자 정의 generator registry entry를
  CLI로 추가하는 공개 명령은 보이지 않았다.
- 로컬 SDK의 `furiosa.kernels.qwen3_vl`에는 32B config JSON만 들어 있다.
  - `common/model_config.py`는 `QWEN3_VL_32B_CONFIG`만 로드.
  - naive wrapper는 32B default config에 `hf_config_overrides`를 적용해 generic entry function을 호출.
  - optimized wrapper도 32B 이름의 optimized EDSL을 8B override shape로 specialization한다.
- 실제 실패 지점은 `optimized/qwen3_vl_32b_w16a16_txt_first.py`의 `hidden_states_pinned` no-op add/layout hint.
  8B shape `[4, Ti, 4096]`에서 compiler tactic을 찾지 못했다.

### 판단

- “Qwen3-VL 8B를 custom model로 generator registry에 추가”하는 방향은 개념적으로 맞다.
- 다만 공개 API로 registry row만 추가하면 되는 구조는 아닌 듯하다. native `furiosa_generator` registry 선택과
  Python `furiosa.kernels.qwen3_vl` entry/kernel path가 함께 맞아야 한다.
- 즉, 가장 현실적인 실험은 설치된 SDK를 직접 덮어쓰기보다 repo-local overlay/venv에서
  `furiosa.kernels.qwen3_vl`을 shadowing하고, 8B config + 8B wrapper + optimized fallback 회피를 검증하는 방식.

### 추천 실험 순서

1. `/usr/local/lib` 직접 수정 금지. workspace에 SDK overlay를 만들고 `PYTHONPATH`로 먼저 로드되게 한다.
2. HF config에서 `Qwen--Qwen3-VL-8B-Instruct.json`을 만들고 `QWEN3_VL_8B_CONFIG`를 추가한다.
3. 8B wrapper를 추가하되, 첫 실험은 optimized text-first path 대신 generic/naive path로 우회한다.
4. 최소 bucket(`max_model_len=256`, `-tp 8`, `-O O0`, `--concurrency 1`)부터 `fxb build` actual compile을 재시도한다.
5. `txt_first`가 통과하면 `txt_mid`, `txt_last`, vision kernels 순으로 다음 실패 kernel을 좁힌다.
6. 모든 kernel이 통과해 FXB가 생성되면 `fxb show`, `fxb inspect`, text-only serve, single-image serve 순으로 검증한다.

## 2026-07-15 — Gemma4 보류, Qwen3-VL 8B FXB 빌드 시도

### 내가 한 것

- `docs/modeldev/2026-07-15_codex_gemma4_build_plan.md` 생성.
  - 결론: Gemma4 12B는 현재 Furiosa supported architecture/로컬 SDK 기준으로 바로 bucket만 채워서
    구동할 수 있는 과제가 아니므로 보류.
  - Qwen3-VL 8B를 먼저 시도하는 방향으로 전환.
- `Qwen/Qwen3-VL-8B-Instruct`를 1 RNGD 목표로 FXB 빌드 검증.
- 환경 측정:
  - 실효 CPU 15
  - `nproc` 128은 호스트 값
  - `/dev/shm` 64MB
  - RAM 1007GB

### 실행 결과

- `fxb build Qwen/Qwen3-VL-8B-Instruct ./qwen3-vl-8b-instruct-rngd.fxb --dry-run -tp 8 --max-model-len 4096 -O O0`
  - exit 0
  - 경고: exact model registry entry 없음.
  - `architecture=Qwen3VLForConditionalGeneration`, `hidden_size=4096`, `intermediate_size=12288`에 대해
    exact entry가 없어 `hidden_size=5120`, `intermediate_size=25600` 쪽 nearest entry로 fallback.
- 실제 4096 build:
  - 실패.
  - `qwen3_vl_32b_w16a16_txt_first_tokenwise`, `tw1024` kernel compile 중
    `failed to lower ... no tactic` 발생.
- 512 fallback:
  - dry-run부터 실패.
  - `Maximum prefill attention_size (512) must equal maximum decode attention_size (256)`.
- 256 fallback:
  - dry-run은 통과.
  - 실제 build는 동일한 `qwen3_vl_32b_w16a16_txt_first_hidden_states_pinned` lowering 실패.
- `tp4, max_model_len=256` fallback:
  - dry-run은 통과.
  - 실제 build는 동일한 `txt_first_tokenwise/tw256` lowering 실패.

### 판단

- 실패 원인은 HF 다운로드나 48GB HBM 부족이 아니라 **현재 Furiosa generator registry에 Qwen3-VL 8B exact entry가
  없고, 32B 계열 generator fallback이 8B BF16 compile을 끝까지 처리하지 못하는 것**으로 보는 게 맞음.
- 따라서 지금 SDK 조합에서는 `Qwen/Qwen3-VL-8B-Instruct`를 1 RNGD에서 바로 FXB로 빌드/서빙하는 단계까지
  진행하지 못했음.
- 다음 후보:
  - Furiosa가 검증한 `Qwen3-VL-32B-Instruct`는 가능성이 높지만 1 RNGD가 아니라 다중 RNGD 목표.
  - 1 RNGD VLM 과제는 Furiosa가 exact registry/preset을 제공하는 더 작은 Qwen3-VL 변형 또는 공식 FP8/FXB가
    있는 모델을 확인한 뒤 진행해야 함.

### 이어받을 때

- `.fxb` 산출물은 생성되지 않았음.
- `furiosa-llm serve` 검증은 build 실패로 실행하지 않았음.
- 같은 명령을 재시도하기보다 Furiosa SDK/FXB registry 업데이트 여부, 또는 official Qwen3-VL 8B FP8/FXB 존재 여부를
  먼저 확인하는 것이 좋음.

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
