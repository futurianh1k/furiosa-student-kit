# 실습 ③: Llama 아티팩트 빌드 (gated 모델 다루기)

> **이 실습의 교훈: 어떤 모델은 다운로드 자체가 막혀 있다.**
> Llama base 가중치는 Meta가 **gated**로 걸어둬서, HF 토큰 없이는 받을 수 없습니다.
> 프리셋(버킷)은 완비되어 있으니, 진짜 관문은 "인증"입니다.

## 대상 모델
`meta-llama/Llama-3.1-8B-Instruct` (프리셋에 append_buckets 있음 ✓, 하지만 gated)

## 먼저 만나는 벽: 403 GatedRepoError
아무 준비 없이 dry-run 하면 이렇게 실패합니다:
```
huggingface_hub.errors.GatedRepoError: 403 Client Error ...
```
이건 버그가 아니라 **접근 권한이 없다**는 뜻입니다.

## 해결: HF 토큰으로 로그인
1. https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct 에서 **Access 요청**(승인 필요)
2. https://huggingface.co/settings/tokens 에서 토큰 발급
3. 로그인:
   ```bash
   huggingface-cli login      # 토큰 붙여넣기
   # 또는:  export HF_TOKEN=hf_xxx
   ```

## Step 1. dry-run (로그인 후)
```bash
bash ../_kit/scripts/check_resources.sh
python build_llama.py --dry-run
```
> 이 폴더의 `build_llama.py`는 Llama 전용 독립 실행본입니다(모델 ID가 박혀 있고,
> 토큰이 안 잡히면 미리 경고). 원본 `_kit/scripts/build_artifact.py`는 안 건드립니다.
`append_buckets`가 0보다 크면(프리셋 있음) `--fix-append` 없이 진행합니다.

## Step 2. 빌드
```bash
python build_llama.py -o ./llama31-8b-artifact
```
> ⚠ 8B 모델이라 0.5B보다 파이프라인·가중치가 큽니다. 15코어 pod에서는 시간이
> 꽤 걸리고 메모리도 더 씁니다. `check_resources.sh`로 RAM 여유를 먼저 보세요.

## Step 3. 검증
```bash
python ../_kit/scripts/verify_artifact.py --artifact ./llama31-8b-artifact 2>&1 | tee verify.log
```

## 생각해볼 점
- gated 모델을 만나면 무엇부터 확인해야 하나? (에러 메시지의 403 / GatedRepo)
- 토큰을 코드/깃에 넣으면 안 되는 이유는? (`HF_TOKEN` 환경변수 / `huggingface-cli login` 사용)

전체 배경: [../_kit/01_GUIDE.md](../_kit/01_GUIDE.md) · [../_kit/02_POSTMORTEM.md](../_kit/02_POSTMORTEM.md)
