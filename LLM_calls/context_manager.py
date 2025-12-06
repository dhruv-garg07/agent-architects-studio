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

def query_llm_with_history(message, history, rag_context, chat_history, **kwargs):
    """
    Query Together AI LLM with the given message and history.
    Args:
        message (str): The latest user message.
        history (list): List of previous messages (dicts or strings).
        rag_context (list): List of dicts with manual/contextual data to include in prompt.
        **kwargs: Additional arguments for stream_chat_response.
    Returns:
        str: The full response from the LLM.
    """
    # USE SQL DB AS THE MEMORY BACKEND LATER
    

    # print("Rag context:", rag_context)

    
    summary = ""
    print(chat_history)
    if chat_history:
        # Create a summary of the chat history
        summary = "\n".join([f"User: {msg['role']}\nAI: {msg['content']}" for msg in chat_history])

    # Build prompt from summary, rag_context, and message
    prompt = system_prompt + "\n\n"
    if rag_context:
        rag_texts = [doc['document'] for doc in rag_context if 'document' in doc]
        prompt += "Relevant Context (manual data):\n" + "\n".join(rag_texts) + "\n\n"
    if summary:
        prompt += f"Conversation History:\n{summary}\n"
    prompt += f"User: {message}\nAI: "
    print("Final Prompt:\n", prompt)

    # Stream and collect the response
    response = ""
    for token in stream_chat_response(prompt, **kwargs):
        response += token
        print(token, end='', flush=True)  # Print tokens as they arrive

    return response


def query_llm_with_history_stream(message, history, rag_context, chat_history, **kwargs):
    """
    Query Together AI LLM with the given message and history.
    Args:
        message (str): The latest user message.
        history (list): List of previous messages (dicts or strings).
        rag_context (list): List of dicts with manual/contextual data to include in prompt.
        **kwargs: Additional arguments for stream_chat_response.
    Returns:
        str: The full response from the LLM.
    """
    # USE SQL DB AS THE MEMORY BACKEND LATER
    

    # print("Rag context:", rag_context)

    
    summary = ""
    print(chat_history)
    if chat_history:
        # Create a summary of the chat history
        summary = "\n".join([f"User: {msg['role']}\nAI: {msg['content']}" for msg in chat_history])

    # Build prompt from summary, rag_context, and message
    prompt = system_prompt + "\n\n"
    if rag_context:
        rag_texts = [doc['document'] for doc in rag_context if 'document' in doc]
        prompt += "Relevant Context (manual data):\n" + "\n".join(rag_texts) + "\n\n"
    if summary:
        prompt += f"Conversation History:\n{summary}\n"
    prompt += f"User: {message}\nAI: "
    print("Final Prompt:\n", prompt)

    # Stream and collect the response
    return stream_chat_response(prompt, **kwargs)
    # response = ""
    # for token in stream_chat_response(prompt, **kwargs):
    #     response += token
    #     print(token, end='', flush=True)  # Print tokens as they arrive

    # return response