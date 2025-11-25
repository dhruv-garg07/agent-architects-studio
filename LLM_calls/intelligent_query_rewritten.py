# Write code to break down the query/task and make a good context for the LLM to answer
import sys
import os
# Get the current file's directory
current_dir = os.path.dirname(__file__) 
# Go two levels up
grandparent_dir = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
# Add to sys.path                   
sys.path.insert(0, grandparent_dir)
from LLM_calls.together_get_response import stream_chat_response, extract_output_after_think

from dotenv import load_dotenv
load_dotenv()
system_prompt = (
    "You are Deepseek, a highly capable, thoughtful, and precise AI assistant. "
    "Understand the user's intent, ask clarifying questions if needed, and provide clear, accurate, and efficient answers. "
    "Be concise, helpful, and never generate images unless explicitly requested."
    "Reply in chat format, in a few sentences only, keep it short and precise."
)

def intelligent_query_rewriter(query: str):
    """
    Rewrite the user's query to be more specific and context-aware.
    Args:
        query (str): The original user query.
    Returns:
        str: The rewritten query.
    """
    # memory = ConversationBufferMemory(return_messages=True)
    
    # memory.save_context({"input": query}, {"output": ""})
    prompt = (
        "You are an expert at rewriting user queries to be more specific and context-aware. "
        "Given the user's query, rewrite it to improve clarity and focus. "
        "Break the query into simpler parts if needed and enable chain of thought reasoning."
        "Use only keywords and context for better rag query."
        "Try to avoid generic phrases like 'Tell me about' or 'Explain', 'and','is', 'the','or', 'but'. "
        "If the query is already clear, return it as is.\n\n"
        f"User Query: {query}\n\n"
        "Rewritten Query:"
    )
    full_response = "".join(
        stream_chat_response(
            prompt=prompt,
            model="ServiceNow-AI/Apriel-1.5-15b-Thinker",
            max_tokens=150,
            temperature=0.3,
            top_p=0.9,
            top_k=5,
            repetition_penalty=0.8,
            stop=["\n\n"],
            verbose=False
        )
    )
    print("full_response: ",full_response)
    rewritten_query = full_response
    return rewritten_query.strip() if rewritten_query else query