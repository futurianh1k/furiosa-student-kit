# claudex-handoff.md — Claude → Codex 작업 인계 (rolling log)

> **용도:** Claude가 한 작업/수정 내역을 동료 Codex에게 전달하는 인계 채널.
> **최신 항목이 맨 위.** 새 작업을 하면 이 파일 위쪽에 항목을 추가한다.
>
> - 협업 규칙: `AGENTS.md` → "에이전트 간 협업 규칙" 참고.
> - 환경 제약(nproc≠실효CPU=15, /dev/shm 64MB), git repo 지도: `AGENTS.md`.
> - 내(Claude) 개인 상세 기록은 `history/`에 별도로 있음(전달용 아님).

---

## 2026-07-15 — Gemma4 12B on RNGD: ❌ NOT FEASIBLE (검증 완료, Codex 문서와 수렴)

**너(Codex)의 `docs/modeldev/2026-07-15_codex_gemma4_build_plan.md` 결론을 확인·확장했어.**
독립적으로 같은 결론(아키텍처 미지원 → Qwen3-VL 선회)에 도달했고, 딥리서치(109 에이전트,
21/25 claim 확인) + 내 로컬 직접 실행으로 근거를 굳혔음.

**핵심 (근본 원인):** `furiosa.models`에 Gemma 구현 클래스가 없음 — 이 pod에서 직접 확인한
노출 클래스는 Exaone4/Exaone/ExaoneMoe/GptOss/Llama/**Mistral/Phi3**/Qwen2/Qwen3/Qwen3Moe/
Qwen3VL 뿐. `google/gemma-4-12B`(클래스 `Gemma4UnifiedForConditionalGeneration`)는
`.build()`에서 `ValueError: unsupported model: ... not available in furiosa.models`로 죽음.

**내가 네 문서에 더한 뉘앙스 4개:**
1. `--dry-run`은 **거짓 양성**이다 — `get_optimized_cls`가 `.build()`(builder.py:219)에서만
   돌아서 버킷만 해석하는 dry-run은 통과함. 초판 README의 "dry-run 통과=성공"은 틀림.
2. 실제 `model_type`은 `gemma`가 아니라 **`gemma4_unified`**, 클래스 `Gemma4UnifiedForConditionalGeneration`.
3. Gemma **4**는 **Apache-2.0·ungated** (gated는 Gemma 3까지) — 초판의 "gated 벽"은 오류.
4. 갭 2층위 구분: (a) 프리셋만 없음=버킷으로 해결(Mistral/Phi3/GptOss/Qwen3-VL, 구현은 있음)
   vs (b) 구현 자체 없음=불가(Gemma). Gemma는 (b).

**내가 바꾼 파일 (검증 완료):**
- `Gemma4_try/build_gemma_TEMPLATE.py` → "벽 진단판"으로 재작성. 버킷 4종은 설계 예시로
  채우고, 빌드 전에 `assert_furiosa_supports()`로 아키텍처 지원을 검사해 fail-fast.
  검증: dry-run 통과(거짓 양성 경고 출력) / 실제 실행 fail-fast(벽 설명 + exit 1).
- `Gemma4_try/README.md` → 두 전제 오류(gated, 무프리셋) 교정, 대체모델 안내 추가.

**이어받을 것 (제안):** 네가 고른 `Qwen/Qwen3-VL-8B-Instruct` 경로를 **실습⑤(진짜로 빌드되는
무프리셋 버킷설계 실습)**으로 만들면 좋겠음. Qwen3-VL/Mistral/Phi3/GptOss 중 15코어·64MB shm
환경에서 실제로 빌드되는지 test-build한 사람은 아직 없음(둘 다 미수행).

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
