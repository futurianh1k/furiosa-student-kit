"""빌드한 아티팩트가 실제로 문제를 고쳤는지 검증한다.

무엇을 확인하나
--------------
1. 추론이 정상 동작하는지 (출력이 나오는지)
2. 로그에서 아래 두 경고가 "사라졌는지"
     - "No extend buckets ..."
     - "Chunked prefill will be disabled ..."
     - "Disabling prefix caching ..."
3. prefix caching 이 실제로 켜졌는지 (is_prefix_cache_enabled: true)

사용법
------
  python verify_artifact.py --artifact ./artifact 2>&1 | tee verify.log

그런 다음 로그에서 위 경고가 없고 is_prefix_cache_enabled: true 가 보이면 성공.
"""

import argparse
from furiosa_llm import LLM, SamplingParams


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifact", default="./artifact", help="빌드한 아티팩트 경로")
    ap.add_argument("--prompt", default="What is the capital of France?")
    args = ap.parse_args()

    with LLM(args.artifact) as llm:
        sp = SamplingParams(min_tokens=10, top_p=0.3, top_k=100)
        msg = [{"role": "user", "content": args.prompt}]
        prompt = llm.tokenizer.apply_chat_template(msg, tokenize=False)
        out = llm.generate([prompt], sp)[0].outputs[0].text
        print("\n=== 모델 출력 ===")
        print(out)
        print("\n※ 위 로그에서 'No extend buckets' / 'Disabling prefix caching' 이 없고")
        print("  'is_prefix_cache_enabled: true' 가 보이면 성공입니다.")


if __name__ == "__main__":
    main()
