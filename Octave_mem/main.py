from RAG_DB.chroma_collection_wrapper import ChromaCollectionWrapper

if __name__ == "__main__":
    wrapper = ChromaCollectionWrapper()
    
    # Single operation with automatic verification
    result = wrapper.create_or_update_collection_with_verify(
        collection_name="research_papers",
        ids=["doc1", "doc2"],
        documents=["Paper on AI", "Paper on IoT"],
        metadatas=[{"author": "Sanket"}, {"author": "John"}]
    )
    
    print("Operation Result:", result["result"])
    print("Verification Success:", result["success"])
    print("Document Count:", result["verification"]["document_count"])
    print("Actual IDs:", result["verification"]["actual_ids"])
    
    # Bulk operations
    operations = [
        {
            "type": "create_or_update",
            "collection_name": "test_collection_1",
            "ids": ["id1", "id2"],
            "documents": ["doc1", "doc2"],
            "metadatas": [{"cat": "A"}, {"cat": "B"}]
        },
        {
            "type": "update",
            "collection_name": "test_collection_1",
            "ids": ["id3"],
            "documents": ["doc3"],
            "metadatas": [{"cat": "C"}]
        },
        {
            "type": "replace",
            "collection_name": "test_collection_1",
            "ids": ["new_id1", "new_id2"],
            "documents": ["new_doc1", "new_doc2"],
            "metadatas": [{"cat": "X"}, {"cat": "Y"}]
        }
    ]
    
    bulk_results = wrapper.bulk_operations_with_verification(operations)
    for i, result in enumerate(bulk_results):
        print(f"\nOperation {i+1}:")
        print(f"Success: {result['success']}")
        print(f"Result: {result['result']}")
        print(f"Document Count: {result['verification'].get('document_count', 'N/A')}")