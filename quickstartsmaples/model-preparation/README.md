# 모델 준비 (아티팩트 빌드) 실습

Furiosa NPU에서 LLM을 돌리려면 모델을 NPU용 **아티팩트**로 빌드해야 합니다.
이 실습은 여러 모델로 그 과정을 직접 해보며, 특히 **이 pod 환경의 함정**
(`nproc` ≠ 실제 CPU, 작은 `/dev/shm`)에 빠지지 않는 법을 익힙니다.

## 시작하기 전에 — 반드시 읽기

먼저 공용 키트의 가이드를 읽으세요. **모든 실습의 전제**입니다.

- 📘 **[_kit/01_GUIDE.md](_kit/01_GUIDE.md)** — 메인 가이드 (이것부터!)
- ✅ **[_kit/CHECKLIST.md](_kit/CHECKLIST.md)** — 실습 중 곁에 두는 체크리스트
- 📕 [_kit/02_POSTMORTEM.md](_kit/02_POSTMORTEM.md) — 왜 이 가이드가 존재하는지 (조교의 실패기)

공용 스크립트는 [`_kit/scripts/`](_kit/scripts/)에 있습니다. 단, **빌드 스크립트는
모델별로 각 폴더에 독립 실행본**을 둡니다(원본 `_kit/scripts/build_artifact.py`는
실습①의 검증된 레퍼런스로 동결). `check_resources.sh`·`verify_artifact.py`는 모델
무관이라 공용 그대로 씁니다.

## 실습 순서 (난이도 순)

| # | 폴더 | 모델 | 배우는 것 | 핵심 관문 |
|---|---|---|---|---|
| ① | [qwen2.5-0.5b/](qwen2.5-0.5b/) | Qwen2.5-0.5B | **레퍼런스(정답 완성본).** append_buckets가 빠진 걸 직접 채워 재빌드 | 버킷 누락 수정 |
| ② | [Qwen3/](Qwen3/) | Qwen3-0.6B | 모든 모델을 고칠 필요는 없다 — dry-run으로 확인 후 그냥 빌드 | 프리셋 이미 완비 |
| ③ | [Llama/](Llama/) | Llama-3.1-8B | gated 모델 다루기 (HF 토큰 인증) | 403 / 로그인 |
| ④ | [Gemma4_try/](Gemma4_try/) | Gemma (도전) | 프리셋이 **없는** 모델 — 버킷을 직접 설계 | 무프리셋 + gated |

> **①번 `qwen2.5-0.5b/`부터 보세요.** 이미 완성된 레퍼런스라, 성공한 빌드/검증
> 스크립트와 로그(`build_and_compile_logs/`)가 그대로 들어 있습니다. 나머지 실습에서
> 막히면 이 폴더의 결과물과 비교하면 됩니다.

## 3원칙 (모든 실습 공통)
1. **`nproc`를 믿지 말고** `_kit/scripts/check_resources.sh`로 실효 CPU를 측정한다.
2. **dry-run 먼저**, 그 다음 빌드.
3. 런타임 시작 **`WARNING`을 끝까지 읽는다**.

## 폴더 구조
```
model-preparation/
├── README.md              ← 지금 이 문서 (실습 인덱스)
├── _kit/                  ← 공용 가이드 + 스크립트 (모든 실습이 공유)
│   ├── 01_GUIDE.md  02_POSTMORTEM.md  CHECKLIST.md  README.md
│   └── scripts/{check_resources.sh, build_artifact.py, verify_artifact.py}
├── qwen2.5-0.5b/          ← 실습① 레퍼런스(공용 build_artifact.py 사용 + 로그)
├── Qwen3/                 ← 실습② (build_qwen3.py — 독립 실행본)
├── Llama/                 ← 실습③ (build_llama.py — 독립 실행본)
└── Gemma4_try/            ← 실습④ 도전 (build_gemma_TEMPLATE.py — 빈 뼈대, 직접 채움)
```
