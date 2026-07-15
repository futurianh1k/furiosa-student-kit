# 실습 체크리스트 (곁에 두고 보세요)

## 빌드 전
- [ ] `bash scripts/check_resources.sh` 실행했다
- [ ] **실효 CPU**를 확인했다 (nproc 128이 아니라 그 아래 숫자!)
- [ ] `/dev/shm`이 작으면(＜1GB) 워커는 1개로 둔다는 걸 안다

## 빌드
- [ ] **먼저 `--dry-run`** 으로 돌렸다
- [ ] dry-run에서 `append_buckets`가 **0이 아님**을 확인했다
- [ ] dry-run에서 `[자원] 실효 CPU=...`가 **자동 측정**됨을 확인했다
- [ ] 워커 CPU를 손으로 넣지 않았다 (스크립트가 자동 계산)
- [ ] 빌드 시작 로그의 **`WARNING` 줄들을 읽었다**

## 빌드 중 — 이상 신호
- [ ] `0/N`에서 안 움직이면 → **멈춘 것.** 실효 CPU/워커 설정 재확인
- [ ] 파이프라인당 수 분 이상 → **틀린 것.** 워커 수를 1로
- [ ] 정상: 파이프라인당 초 단위, 작은 모델은 10여 분 내 완료

## 검증
- [ ] `verify_artifact.py` 출력이 정상적으로 나온다
- [ ] 로그에 `No extend buckets` / `Disabling prefix caching`이 **없다**
- [ ] 로그에 `is_prefix_cache_enabled: true`가 **있다**

---

## 절대 하지 말 것
- ❌ `nproc` 숫자로 워커/CPU를 잡는다
- ❌ "워커 많을수록 빠르겠지" (여긴 shm이 작아 오히려 느려짐)
- ❌ dry-run 없이 바로 실제 빌드
- ❌ 시작 로그의 WARNING을 건너뛰고 진행 막대만 본다

## 막히면
1. `scripts/check_resources.sh` 다시 실행
2. `02_POSTMORTEM.md` 맨 끝 "빠른 진단 체크리스트"
3. 그래도 안 되면 조교 호출 (증상 + `check_resources.sh` 출력 함께)
