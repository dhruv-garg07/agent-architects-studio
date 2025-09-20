import os
import uuid
import chromadb
from dotenv import load_dotenv
load_dotenv()

import os
import chromadb

def get_chroma_cloud_client():
    """
    Returns a Chroma CloudClient for the default database in the tenant.
    CHROMA_API_KEY and CHROMA_TENANT must be set in environment variables.
    """
    api_key = os.getenv("CHROMA_API_KEY")
    tenant = os.getenv("CHROMA_TENANT")

    if not api_key or not tenant:
        raise ValueError("CHROMA_API_KEY and CHROMA_TENANT must be set in env variables.")

    # CloudClient automatically uses the default database for the tenant
    client = chromadb.CloudClient(tenant=tenant, api_key=api_key)
    print(f"CloudClient ready for tenant '{tenant}' with default database")
    return client


# Example usage
if __name__ == "__main__":
    client = get_chroma_cloud_client()
    collection = client.get_or_create_collection("user_chat_history")
    collection.add(documents=["Hello world"], ids=["doc1"])
