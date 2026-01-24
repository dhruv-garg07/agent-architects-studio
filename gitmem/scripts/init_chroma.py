import chromadb
from chromadb.config import Settings
import os

def init_chroma():
    path = "./gitmem_data/indexes"
    print(f"Initializing ChromaDB at {path}...")
    
    # Ensure directory exists
    os.makedirs(path, exist_ok=True)
    
    try:
        client = chromadb.PersistentClient(path=path)
        # Create default collection
        collection = client.get_or_create_collection(name="gitmem_global")
        print(f"Collection 'gitmem_global' check: {collection.count()} items.")
        print("ChromaDB initialization complete.")
    except Exception as e:
        print(f"Error initializing ChromaDB: {e}")

if __name__ == "__main__":
    init_chroma()
