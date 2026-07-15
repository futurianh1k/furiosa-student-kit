from dotenv import load_dotenv
load_dotenv()
from furiosa_llm import LLM, SamplingParams

# 새로 빌드한 로컬 아티팩트 사용 (기존 허브 모델명 대신 경로)
with LLM("./qwen2.5-0.5b-artifact") as llm:
    sp = SamplingParams(min_tokens=10, top_p=0.3, top_k=100)
    msg = [{"role": "user", "content": "What is the capital of France?"}]
    prompt = llm.tokenizer.apply_chat_template(msg, tokenize=False)
    print(llm.generate([prompt], sp)[0].outputs[0].text)
