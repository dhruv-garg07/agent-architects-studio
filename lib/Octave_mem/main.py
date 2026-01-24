from RAG_DB.chroma_collection_wrapper import ChromaCollectionWrapper
import os
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    wrapper = ChromaCollectionWrapper(database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY"))
    
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
    
    
    print("\nFetching Collection Info:", wrapper.get_collection_info("research_papers"))
    # Create_or_update is used to add new documents or update existing ones.
    # Update is used to overwrite a particular document by its ID.
    # Replace is used to completely replace the collection with new data.
    # In this case, "replace" will remove all existing documents and add the new ones.
    
    # Bulk operations
    # operations = [
    #     {
    #         "type": "create_or_update",
    #         "collection_name": "test_collection_1",
    #         "ids": ["id6", "id4"],
    #         "documents": ["doc1123", "doc122"],
    #         "metadatas": [{"cat": "1234213"}, {"cat234": "q134223"}]
    #     },
        
    #     {
    #         "type": "update",
    #         "collection_name": "test_collection_1",
    #         "ids": ["id7"],
    #         "documents": ["doc4"],
    #         "metadatas": [{"cats": "D"}]
    #     }
    #     # {
    #     #     "type": "replace",
    #     #     "collection_name": "test_collection_1",
    #     #     "ids": ["new_id1", "new_id2"],
    #     #     "documents": ["new_doc1", "new_doc2"],
    #     #     "metadatas": [{"cat": "X"}, {"cat": "Y"}]
    #     # }
    # ]
    
    # bulk_results = wrapper.bulk_operations_with_verification(operations)
    # for i, result in enumerate(bulk_results):
    #     print(f"\nOperation {i+1}:")
    #     print(f"Success: {result['success']}")
    #     print(f"Result: {result['result']}")
    #     print(f"Document Count: {result['verification'].get('document_count', 'N/A')}")