from RAG_DB.chroma_reader import ChromaReader
from RAG_DB.chroma_collection_manager import ChromaCollectionManager

if __name__ == "__main__":
    reader = ChromaReader()

    # 🔍 Search without metadata filter
    results = reader.search(
        collection_name="my_collection",
        query="Chroma",
        n_results=2
    )
    print("Results (no filter):", results)

    # 🔍 Search with metadata filter
    filtered_results = reader.search(
        collection_name="my_collection",
        query="Chroma",
        metadata_filter = {
            "$and": [
                {"author": "Sanket"},
                {"topic": "example"}
            ]
        }
    )
    print("Results (with filter):", filtered_results)

    
    # COLLECTION MGMT
    manager = ChromaCollectionManager()

    # 1️⃣ Create empty collection
    print(manager.create_collection("new_empty_collection"))

    # 2️⃣ Create collection with data
    print(manager.create_collection(
        collection_name="research_papers",
        ids=["doc1", "doc2"],
        documents=["Paper on AI", "Paper on IoT"],
        metadatas=[{"author": "Sanket"}, {"author": "John"}]
    ))

    # 3️⃣ Try to create an already existing collection
    print(manager.create_collection("research_papers"))
