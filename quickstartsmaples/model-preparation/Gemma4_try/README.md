# 실습 ④ (심화·도전): Gemma — 지원 프리셋이 없는 모델

> **이 실습의 교훈: 프리셋이 없으면 버킷을 "직접" 설계해야 한다.**
> 디렉터리 이름이 `Gemma4_try`("try")인 이유입니다. 앞의 세 실습과 달리 정답이
> 주어져 있지 않습니다. 두 개의 벽을 스스로 넘어야 합니다.

## 두 개의 벽

### 벽 1: gated 다운로드
Gemma도 gated입니다(실습 ③ Llama와 동일). 먼저 HF 토큰으로 로그인해야 합니다.
```bash
huggingface-cli login
```

### 벽 2: **프리셋이 없다**
Furiosa의 `presets.py`에는 `qwen2 / exaone4 / llama / qwen3 / qwen3_moe`만 있고
**gemma는 없습니다.** 그래서 버킷을 비운 채 빌드하면 이렇게 실패합니다:
```
No bucket configuration provided and no matching bucket preset found
for model_type=gemma... Please provide explicit bucket configuration.
```
즉 `--fix-append` 정도가 아니라, **4종 버킷을 전부 직접 정의**해야 합니다.

## 무엇을 해야 하나 (직접 설계)

원본 `build_artifact.py`는 프리셋/`--fix-append`만 지원하므로, 이 실습은 **버킷을
직접 설계**해야 합니다. 이 폴더에 뼈대 파일 `build_gemma_TEMPLATE.py`를 넣어 두었습니다
(원본 `_kit/scripts/build_artifact.py`는 건드리지 않았습니다). 파일 안 `GEMMA_*` 상수
4종이 **비어 있으니 여러분이 채우세요**(안 채우면 의도적으로 멈춥니다). 참고 자료:

- 버킷 4종의 의미와 형식: [../_kit/01_GUIDE.md](../_kit/01_GUIDE.md), `presets.py`의 다른 모델 예시
- 4종을 **전부** 채워야 함(부분 지정 금지): `prefill_buckets`, `decode_buckets`,
  `append_buckets`, `tokenwise_seq_lens`
- 값 잡는 감각: 실습 ①의 `_kit/scripts/build_artifact.py` 안 `QWEN25_05B_*` 상수와,
  `presets.py`의 `LLAMA_3_1_8B_PRESET`을 참고해 Gemma 크기에 맞게 조정

## 최소 절차
1. `bash ../_kit/scripts/check_resources.sh` — 자원 확인
2. `huggingface-cli login` — gated 라 토큰 로그인
3. `build_gemma_TEMPLATE.py`를 열어 `MODEL_ID` 확인/교체 + `GEMMA_PREFILL/DECODE/
   APPEND/TOKENWISE` 4종을 직접 채움
4. **먼저 `python build_gemma_TEMPLATE.py --dry-run`** 으로 "no matching preset" 없이
   버킷이 해석되는지 확인
5. `python build_gemma_TEMPLATE.py -o ./gemma-artifact` → `verify_artifact.py`로 검증

## 성공/실패의 기준
- dry-run에서 `append_buckets`가 0보다 크고 에러가 없으면 설계 성공
- 빌드가 `0/N`에서 멈추면 → 버킷 값이 아니라 **자원 설정** 문제 (워커 CPU ≤ 실효 CPU)
- 이 실습은 "안 될 수도 있다"가 정상입니다. 어디서 왜 막히는지 기록하는 것 자체가 목표.

## 생각해볼 점
- 프리셋이 없는 모델을 지원하려면 무엇을 알아야 하나? (모델 구조 → 버킷 설계)
- gated + 무프리셋이 겹칠 때, 어떤 순서로 문제를 좁혀야 하나?

전체 배경: [../_kit/01_GUIDE.md](../_kit/01_GUIDE.md) · [../_kit/02_POSTMORTEM.md](../_kit/02_POSTMORTEM.md)
