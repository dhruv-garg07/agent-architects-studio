from together import Together
import os
from dotenv import load_dotenv
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
load_dotenv()


import time
from together import Together
from requests.exceptions import RequestException
import traceback


# response = stream_chat_response(prompt=str(messages))
#         full_response = ""
#         for token in response:
#             full_response+=token
#         response = extract_output_after_think(full_response)

# TOGETHER_API_KEY = "<YOUR_API_KEY_HERE>"

def extract_output_after_think(response: str) -> str:
    """
    Extracts and returns the part of the response after the </think> tag.
    If the tag is not found, returns the original response.
    """
    try:
        end_tag = "</think>"
        if end_tag in response:
            return response.split(end_tag, 1)[1].strip()
    except:
        return response  # fallback if tag not present

def stream_chat_response(
    prompt: str,
    model: str = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
    max_tokens: int = 5000,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 50,
    repetition_penalty: float = 1.0,
    stop: list = None,
    max_retries: int = 3,
    verbose: bool = True
):
    """
    Streams response from Together AI with retry and latency logging.

    Args:
        prompt (str): User prompt.
        model (str): Model name.
        max_tokens (int): Maximum tokens to generate.
        temperature (float): Sampling temperature.
        top_p (float): Nucleus sampling (top-p).
        top_k (int): Top-k sampling.
        repetition_penalty (float): Penalizes repetition.
        stop (list): Stop sequences.
        max_retries (int): Retry attempts on failure.
        verbose (bool): Whether to print latency.

    Yields:
        str: The streamed content.
    """
    client = Together(api_key=TOGETHER_API_KEY)
    retry_count = 0

    while retry_count < max_retries:
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                stop=stop,
                stream=True
            )

            # Begin streaming
            for chunk in response:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    yield delta.content

            end_time = time.time()
            if verbose:
                print(f"\nTotal latency: {end_time - start_time:.2f} seconds")
            break  # successful run

        except (RequestException, Exception) as e:
            retry_count += 1
            print(f" Error occurred (attempt {retry_count}/{max_retries}): {e}")
            traceback.print_exc()
            if retry_count >= max_retries:
                print("Maximum retries exceeded.")
                break
            time.sleep(1)  # small delay before retry


if __name__ == "__main__":
    prompt = "Tell me some underrated travel destinations in South America."

    print("🧠 AI Response:\n")
    for word in stream_chat_response(
        prompt,
        max_tokens=3000,
        temperature=0.8,
        top_p=0.95,
        top_k=40,
        repetition_penalty=1.1,
        stop=["User:", "AI:"],
        max_retries=3
    ):
        print(word, end='', flush=True)
