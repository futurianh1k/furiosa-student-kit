# 코드 리뷰 — model-preparation/_kit/scripts

- **날짜:** 2026-07-15
- **리뷰어:** Claude (Claude Code)
- **대상:** `quickstartsmaples/model-preparation/_kit/scripts/`
  - `build_artifact.py`
  - `check_resources.sh`
  - `verify_artifact.py`

전반적으로 교육 의도("nproc를 믿지 말고 cgroup 실효 CPU를 측정하라")가 코드에 잘 녹아 있다.
다만 **정작 그 교훈을 깨뜨릴 수 있는 구멍이 하나** 있다.

---

## 🔴 1. `--workers`가 자원 상한 검증을 우회한다 (이 키트의 존재 이유를 무력화)

`build_artifact.py:97-102`의 검증은 **워커 1개당** CPU만 본다:

```python
cpu_per_worker = args.cpu_per_worker or max(1, eff - 1)   # eff=15 → 14
if cpu_per_worker > eff:      # 14 > 15? No → 통과
    raise SystemExit(...)
```

그런데 실제 ray에 넘기는 건 `num_pipeline_builder_workers=args.workers`이고,
각 워커가 `cpu_per_worker`를 요청한다 (`build_artifact.py:137-143`).
학생이 `--workers 2`를 주면 **2 × 14 = 28 CPU를 15코어 pod에 요청** → ray가 워커 배치
실패 → 빌드 정체. 이건 `02_POSTMORTEM.md`에 기록된 "5시간 날린" 바로 그 실패 모드다.

`check_resources.sh`는 `--num-compile-workers 1`을 하드코딩으로 권고하는데,
`build_artifact.py`는 그 불변식을 깰 수 있는 손잡이를 열어두고 검증은 하지 않는다.

**수정 (총량으로 검증):**

```python
if args.workers * cpu_per_worker > eff:
    raise SystemExit(
        f"워커 {args.workers} × 워커당 {cpu_per_worker} = {args.workers*cpu_per_worker} "
        f"> 실효 CPU({eff}). 워커 수 또는 --cpu-per-worker를 줄이세요."
    )
```

---

## 🟡 2. verify_artifact.py: `add_generation_prompt` 누락

`verify_artifact.py:32`:

```python
prompt = llm.tokenizer.apply_chat_template(msg, tokenize=False)
```

`add_generation_prompt=True`가 빠져 있어 assistant 턴 프라이머
(`<|im_start|>assistant`)가 붙지 않는다. 그러면 모델이 사용자 발화를 이어 쓰거나
이상한 출력을 낼 수 있어, "출력이 정상인지" 확인하려는 검증 목적과 어긋난다.

**수정:** `apply_chat_template(msg, tokenize=False, add_generation_prompt=True)`

---

## 🟡 3. 라이브러리 private 속성 접근

`build_artifact.py:123,127`에서 `builder._buckets`, `builder._max_model_len`를 직접 쓴다.
dry-run 검증의 핵심이라 이해는 되지만, `furiosa_llm` 버전이 올라가면 조용히 깨진다
(밑줄 = 비공개 API).

**수정:** 최소한 `getattr(builder, "_buckets", None)`로 감싸고, 없으면 안내 메시지를
내도록 하는 게 학생 배포용으로 안전하다.

---

## 🟢 4. 사소한 것

- `verify_artifact.py:8` 독스트링: "아래 **두** 경고"라 해놓고 bullet은 3개다 ("두" → "세").
- `build_artifact.py:44,52,55`에서 `import os`를 함수 안에서 3번 반복 —
  파일 상단으로 올리면 깔끔하다.
- `check_resources.sh`는 견고하다 (cgroup v2/v1/폴백, `set -euo pipefail`,
  `shm<1024` 경고). 특별한 문제 없음.

---

## 요약

심각한 건 **#1 하나**다 — 이 키트의 목적이 "자원 초과 요청 방지"인데 `--workers`로
그걸 우회할 수 있으니 총량 검증을 꼭 넣어야 한다. #2, #3은 학생이 겪을 실제 혼란을 줄여준다.

| # | 심각도 | 위치 | 요지 |
|---|--------|------|------|
| 1 | 🔴 High | `build_artifact.py:97-102` | `--workers`가 자원 상한 검증 우회 → 빌드 정체 |
| 2 | 🟡 Med | `verify_artifact.py:32` | `add_generation_prompt=True` 누락 |
| 3 | 🟡 Med | `build_artifact.py:123,127` | private 속성(`_buckets`, `_max_model_len`) 직접 접근 |
| 4 | 🟢 Low | 여러 곳 | 독스트링 오타, `import os` 반복 |
