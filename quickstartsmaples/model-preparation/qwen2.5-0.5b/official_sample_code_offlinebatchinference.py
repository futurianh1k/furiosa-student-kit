from dotenv import load_dotenv
load_dotenv() # .env 파일 자동 로드

from furiosa_llm import LLM, SamplingParams

# Load the model from Hugging Face model hub
with LLM("furiosa-ai/Qwen2.5-0.5B-Instruct") as llm:
    # You can specify various parameters for text generation
    sampling_params = SamplingParams(min_tokens=10, top_p=0.3, top_k=100)

    # Prompt for the model
    message = [{"role": "user", "content": "What is the capital of France?"}]
    prompt = llm.tokenizer.apply_chat_template(message, tokenize=False)

    # Generate text
    response = llm.generate([prompt], sampling_params)

    # Print the output of the model
    print(response[0].outputs[0].text)