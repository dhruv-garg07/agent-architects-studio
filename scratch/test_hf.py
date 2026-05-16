import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path so we can import from Octave_mem
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from Octave_mem.RAG_DB.chroma_collection_manager import RemoteEmbeddingClient
    
    load_dotenv(override=True)
    hf_token = os.getenv("HF_TOKEN")
    
    if not hf_token:
        print("[ERROR] HF_TOKEN not found in environment variables.")
        sys.exit(1)
        
    print(f"[START] Testing Hugging Face Inference API with token: {hf_token[:4]}...{hf_token[-4:]}")
    
    client = RemoteEmbeddingClient()
    test_text = "Hello, world! Testing Hugging Face connection."
    
    print("[WAIT] Sending request to Hugging Face...")
    vector = client.embed_remote([test_text])[0]
    
    print(f"[SUCCESS] Received vector of length: {len(vector)}")
    print(f"[DATA] Sample (first 5 values): {vector[:5]}")

except Exception as e:
    print(f"[FAILED] Failed to connect to Hugging Face: {e}")
