# 실습 ②: Qwen3 아티팩트 빌드

> **이 실습의 교훈: 모든 모델을 고쳐야 하는 건 아니다.**
> Qwen2.5-0.5B(실습 ①)는 프리셋에 `append_buckets`가 빠져 있어 직접 채워야 했지만,
> Qwen3는 프리셋에 **이미 들어 있습니다.** dry-run으로 그걸 확인하고 그냥 빌드하면 됩니다.

## 대상 모델
`Qwen/Qwen3-0.6B` (작아서 실습에 적당, pod 캐시에 있음)

## 먼저: 자원 확인
```bash
bash ../_kit/scripts/check_resources.sh
```

## Step 1. dry-run — `--fix-append` **없이**
```bash
python build_qwen3.py --dry-run
```
> 이 폴더의 `build_qwen3.py`는 Qwen3 전용 독립 실행본입니다(모델 ID가 박혀 있음).
> 원본 `_kit/scripts/build_artifact.py`는 Qwen2.5 레퍼런스로 그대로 두었습니다.
이렇게 나오면 정상입니다:
```
Found bucket preset for model_type=qwen3, ...
append_buckets : 33   ← 0이 아님! → 손댈 필요 없음
→ 총 파이프라인 약 68개
```
`append_buckets`가 **0이 아니므로** `--fix-append`가 필요 없습니다.
(만약 0이었다면 실습 ①처럼 직접 채워야 합니다.)

## Step 2. 빌드
```bash
python build_qwen3.py -o ./qwen3-0.6b-artifact
```
> ⚠ 파이프라인이 68개입니다(Qwen2.5의 14개보다 훨씬 많음). 15코어 pod에서는
> Qwen2.5보다 오래 걸립니다. `0/68`에서 멈추는 게 아니라 **천천히 증가**하면 정상입니다.

## Step 3. 검증
```bash
python ../_kit/scripts/verify_artifact.py --artifact ./qwen3-0.6b-artifact 2>&1 | tee verify.log
```

## 생각해볼 점
- Qwen2.5-0.5B는 왜 append가 빠졌고 Qwen3-0.6B는 왜 있을까? (프리셋 관리의 차이)
- 파이프라인 68개 vs 14개 차이는 어디서 오나? (버킷 조합 수)

전체 배경: [../_kit/01_GUIDE.md](../_kit/01_GUIDE.md) · [../_kit/02_POSTMORTEM.md](../_kit/02_POSTMORTEM.md)
