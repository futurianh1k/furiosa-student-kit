# 실습 ④ (심화·도전): Gemma 4 12B — "지원되지 않는 아키텍처"의 벽

> **이 실습의 진짜 교훈: 버킷을 못 채워서가 아니라, Furiosa가 이 아키텍처를
> 아예 구현하지 않아서 막힌다.** 디렉터리 이름이 `Gemma4_try`("try")인 이유입니다.
> "안 될 수도 있다"가 정상 — **어디서 왜 막히는지 정확히 진단·기록하는 것**이 목표.

> ⚠️ **검증 결론 (2026-07-15, 딥리서치 + Codex + 로컬 직접 실행 3중 확인).**
> 아래는 초판 README의 잘못된 전제를 교정한 내용입니다. 전체 근거:
> [../../../docs/handoff/claudex-handoff.md](../../../docs/handoff/claudex-handoff.md) ·
> [../../../docs/modeldev/2026-07-15_codex_gemma4_build_plan.md](../../../docs/modeldev/2026-07-15_codex_gemma4_build_plan.md)

## 결론: 현재 Furiosa RNGD에서 Gemma 4 12B는 빌드 불가 (NOT FEASIBLE)

`furiosa.models`가 구현한 아키텍처는 이 pod 기준 다음뿐입니다:
`Exaone4 / Exaone / ExaoneMoe / GptOss / Llama / Mistral / Phi3 / Qwen2 / Qwen3 / Qwen3Moe / Qwen3VL`.
**Gemma는 없습니다.** Furiosa는 `getattr(furiosa.models, <HF아키텍처클래스명>)`로 구현체를
찾는데, Gemma 4 12B의 클래스 `Gemma4UnifiedForConditionalGeneration`이 없어서 실제 빌드가
이렇게 죽습니다:

```
ValueError: unsupported model: the class
            'Gemma4UnifiedForConditionalGeneration' not available in furiosa.models
```

## 초판의 전제 오류 2가지 (교정)

### ❌→✅ 벽 1: "gated" — Gemma 4는 gated가 아니다
Gemma **4**는 **Apache-2.0 · ungated**입니다. HF 토큰이 필요 없습니다.
(gated인 것은 Gemma **3**까지 — 초판 템플릿이 기본값을 `gemma-3-1b-it`으로 둬서 세대가
뒤섞였음.)

### ❌→✅ 벽 2: "프리셋만 없다"가 아니라 "아키텍처 구현이 없다"
초판은 "presets.py에 gemma가 없으니 버킷 4종을 채우면 된다"고 했지만 **틀렸습니다.**
`model_type`도 `gemma`가 아니라 `gemma4_unified`이고, 근본 문제는 **버킷이 아니라 구현**입니다.

| 갭 | 고칠 수 있나 | 해당 모델 |
|---|---|---|
| (a) 프리셋만 없음 | ✅ BucketConfig 직접 설계로 해결 | Mistral · Phi3 · GptOss · Qwen3-VL (구현은 있음) |
| (b) **아키텍처 구현 자체가 없음** | ❌ **버킷으로 절대 불가** | **Gemma (여기 해당)** |

## ⚠️ 함정: `--dry-run`은 통과한다 (거짓 양성)

`get_optimized_cls`는 `.build()` 시점(`builder.py:219`)에만 실행됩니다. 그래서
`--dry-run`(버킷만 해석)은 **성공**하고, 실제 빌드에서만 위 `ValueError`가 터집니다.
→ 초판의 "dry-run 통과 = 성공" 기준은 Gemma에선 **거짓 양성**입니다.

이 폴더의 `build_gemma_TEMPLATE.py`는 이 함정을 반영해, 버킷을 예시로 채워두되 **빌드 전에
아키텍처 지원을 스스로 검사(fail-fast)** 하도록 다시 작성됐습니다.

## 실습 절차 (벽을 직접 확인)
```bash
bash ../_kit/scripts/check_resources.sh          # 0) 자원 확인
python build_gemma_TEMPLATE.py --dry-run         # 1) 버킷은 통과 — 단, 이건 거짓 양성
python build_gemma_TEMPLATE.py -o ./gemma-artifact  # 2) 아키텍처 검사에서 fail-fast → 벽 확인
# (진짜 ValueError 를 직접 보고 싶으면:  --skip-arch-check 로 곧장 빌드 시도)
```

## Gemma 4 12B 아키텍처 (참고, config.json 실측)
48층 · hidden 3840 · heads 16 · **KV heads 8(GQA)** · head_dim 256 · vocab 262144 ·
max_pos 262144(256K) · sliding_window 1024 · gelu_pytorch_tanh · bf16 · ~11.95B.
**멀티모달·encoder-free**(raw 이미지패치+오디오웨이브폼 직접 투영) · thinking mode.
하드웨어는 문제 아님(BF16 24GB / FP8 12GB → 48GB 카드 1장에 여유). 즉 **막는 건 오직
소프트웨어 아키텍처 지원**.

## 실제로 "버킷 설계"를 실습하고 싶다면 → 대체 모델
구현은 있고 **프리셋만 없는** 모델로 바꾸면, 버킷을 직접 설계해야 하고 **실제로 빌드됩니다**:
`Mistral` · `Phi3` · `GptOss` · `Qwen3-VL`.
(Codex도 같은 이유로 `Qwen/Qwen3-VL-8B-Instruct`로 선회함 →
[../../../docs/modeldev/2026-07-15_codex_gemma4_build_plan.md](../../../docs/modeldev/2026-07-15_codex_gemma4_build_plan.md))

## 생각해볼 점
- "지원 안 됨"에도 두 층위가 있다: **프리셋 부재(버킷으로 해결)** vs **구현 부재(불가)**.
  주어진 모델이 어느 쪽인지 어떻게 판별하나? (→ `furiosa.models`에 클래스가 있는지 확인)
- `--dry-run` 통과가 왜 "성공"을 보장하지 못하나? (검사·컴파일이 `.build()`에서만 일어남)
- Furiosa가 Gemma를 지원하려면 무엇이 필요한가? (`furiosa.models`에 Gemma 구현 +
  멀티모달용 비전/오디오 투영 + `presets.py` 프리셋)

전체 배경: [../_kit/01_GUIDE.md](../_kit/01_GUIDE.md) · [../_kit/02_POSTMORTEM.md](../_kit/02_POSTMORTEM.md)
