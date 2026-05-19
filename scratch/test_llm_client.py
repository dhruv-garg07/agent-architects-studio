import os
import sys

# Add parent directory to path for imports
project_root = "/Users/gargdhruv/Desktop/agent-architects-studio"
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'lib'))

from SimpleMem.utils.llm_client import LLMClient

def test_init():
    print("Loading LLMClient...")
    client = LLMClient()
    print("LLMClient initialized.")
    print(f"claude_api_key: {'Loaded (starts with ' + client.claude_api_key[:10] + '...)' if client.claude_api_key else 'None'}")
    print(f"claude_model: {client.claude_model}")
    print(f"anthropic_client: {client.anthropic_client}")

if __name__ == "__main__":
    test_init()
