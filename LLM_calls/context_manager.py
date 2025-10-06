# Make calls to RAG DB from here.
import os
import sys
# import sys, os
sys.path.append(os.path.dirname(__file__))
# Get the current file's directory
current_dir = os.path.dirname(__file__)

# Get the parent directory (one level up)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

# Add parent directory to sys.path
sys.path.insert(0, parent_dir)
print(parent_dir)
import sys
import os

# Get the current file's directory
current_dir = os.path.dirname(__file__)

# Go two levels up
grandparent_dir = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))

# Add to sys.path
sys.path.insert(0, grandparent_dir)

from LLM_calls.together_get_response import stream_chat_response, extract_output_after_think

system_prompt = (
    "You are Deepseek, a highly capable, thoughtful, and precise AI assistant. "
    "Understand the user's intent, ask clarifying questions if needed, and provide clear, accurate, and efficient answers. "
    "Be concise, helpful, and never generate images unless explicitly requested."
    "Reply in chat format, in a few sentences only, keep it short and precise."
)

def query_llm_with_history(message, history, **kwargs):
    """
    Query Together AI LLM with the given message and history.
    Args:
        message (str): The latest user message.
        history (list): List of previous messages (dicts or strings).
        **kwargs: Additional arguments for stream_chat_response.
    Returns:
        str: The full response from the LLM.
    """
    # Build prompt from history and message
    prompt = ""
    prompt += system_prompt + "\n\n"
    if history:
        for h in history:
            if isinstance(h, dict):
                role = h.get('role', 'user')
                content = h.get('content', str(h))
                prompt += f"{role.capitalize()}: {content}\n"
            else:
                prompt += str(h) + "\n"
    prompt += f"User: {message}\nAI: "

    # Stream and collect the response
    response = ""
    for token in stream_chat_response(prompt, **kwargs):
        response += token
        print(token, end='', flush=True)  # Print tokens as they arrive

    return extract_output_after_think(response)