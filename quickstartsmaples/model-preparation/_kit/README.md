# Furiosa 아티팩트 빌드 실습 키트

Furiosa NPU에서 LLM 아티팩트를 **직접 빌드**하는 실습 자료입니다.
이 키트의 목적은 단순히 빌드 방법을 알려주는 게 아니라, **컨테이너 환경의 함정
(`nproc` ≠ 실제 CPU, 작은 `/dev/shm`)에 빠지지 않도록** 하는 것입니다.
조교가 실제로 이 함정에 빠져 5시간을 태운 기록을 바탕으로 만들었습니다.

## 무엇부터 볼까

| 순서 | 파일 | 용도 |
|---|---|---|
| 1 | **[01_GUIDE.md](01_GUIDE.md)** | 메인 가이드. 이것부터 읽으세요. |
| 2 | **[CHECKLIST.md](CHECKLIST.md)** | 실습 중 곁에 두는 한 장 체크리스트 |
| 참고 | [02_POSTMORTEM.md](02_POSTMORTEM.md) | 왜 이 가이드가 존재하는지 (실패의 전체 기록) |

## 스크립트 (`scripts/`)

| 파일 | 언제 | 한 줄 설명 |
|---|---|---|
| `check_resources.sh` | 빌드 전 항상 | pod의 **실제** CPU/shm 측정 + 빌드 권고값 출력 |
| `build_artifact.py` | 빌드 | dry-run/빌드. 워커 CPU를 **자동으로 측정**해 설정 |
| `verify_artifact.py` | 빌드 후 | 경고가 사라졌는지 검증 |
| `streamlit_artifact_chat.py` | 데모 | 로컬 artifact를 웹 UI에서 채팅으로 실행 |

## 30초 시작

```bash
cd scripts
bash check_resources.sh                                                   # 0. 자원 확인
python build_artifact.py --model Qwen/Qwen2.5-0.5B-Instruct --fix-append --dry-run   # 1. 검증
python build_artifact.py --model Qwen/Qwen2.5-0.5B-Instruct --fix-append -o ./out    # 2. 빌드
python verify_artifact.py --artifact ./out 2>&1 | tee verify.log          # 3. 확인
```

## 로컬 artifact 채팅 UI

```bash
pip install streamlit
cd quickstartsmaples/model-preparation/_kit/scripts
streamlit run streamlit_artifact_chat.py
```

기본 artifact 경로는 `../../qwen2.5-0.5b/qwen2.5-0.5b-artifact`입니다.

## 요구 사항
- Furiosa NPU가 있는 pod (이 실습용 환경)
- `furiosa-llm`이 설치된 파이썬 환경
- 인터넷(HF에서 베이스 모델을 받으므로) 또는 미리 캐시된 모델

## 이 키트가 지키게 하는 3원칙
1. `nproc`를 믿지 말고 **cgroup 실효 CPU를 측정**한다.
2. **dry-run 먼저**, 그 다음 빌드.
3. 런타임 시작 **`WARNING`을 끝까지 읽는다**.
