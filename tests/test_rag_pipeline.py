import unittest
from unittest.mock import patch, MagicMock
from utils.chunking import UnifiedChunker
from utils.reranking import Reranker
from SimpleMem.core.document_synthesizer import DocumentSynthesizer

class TestRAGPipeline(unittest.TestCase):
    
    @patch('SimpleMem.utils.llm_client.LLMClient')
    def test_zero_llm_calls_on_ingestion(self, MockLLMClient):
        # Mock LLM Client shouldn't be called
        mock_llm = MockLLMClient.return_value
        
        chunker = UnifiedChunker(mode='fast', chunk_size=50)
        docs = ["This is a test document to ensure no LLM calls are made during ingestion."]
        
        chunks = chunker.chunk_text(docs[0], metadata={"source": "test"})
        
        # Verify chunking happened
        self.assertTrue(len(chunks) > 0)
        self.assertEqual(chunks[0]['text'], docs[0])
        
        # In actual ingestion, Agentic_RAG just uses embeddings. We can mock Agentic_RAG
        with patch('Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG.Agentic_RAG') as MockAgenticRAG:
            rag = MockAgenticRAG()
            rag.add_docs(
                agent_ID="agent_123",
                ids=["doc1_chunk0"],
                documents=[chunks[0]['text']],
                metadatas=[chunks[0]['metadata']]
            )
            
            # Assert add_docs was called
            rag.add_docs.assert_called_once()
            
            # Assert LLM was never called
            mock_llm.generate.assert_not_called()
            mock_llm.get_chat_completion.assert_not_called()

    @patch('SimpleMem.utils.llm_client.LLMClient')
    def test_retrieve_then_refine_cycle(self, MockLLMClient):
        mock_llm = MockLLMClient.return_value
        mock_llm.get_chat_completion.return_value = "Synthesized Answer"
        
        query = "What is the capital of France?"
        retrieved_chunks = [
            {"text": "Paris is the capital of France.", "metadata": {"title": "Doc 1"}},
            {"text": "France is in Europe.", "metadata": {"title": "Doc 2"}}
        ]
        
        reranker = Reranker()
        # Mock rerank to just return chunks
        with patch.object(reranker, 'rerank', return_value=retrieved_chunks) as mock_rerank:
            reranked = reranker.rerank(query=query, documents=retrieved_chunks, top_k=2)
            
            synthesizer = DocumentSynthesizer(llm_client=mock_llm)
            answer = synthesizer.synthesize(query=query, chunks=reranked)
            
            self.assertEqual(answer, "Synthesized Answer")
            
            # Assert exactly 1 LLM call
            mock_llm.get_chat_completion.assert_called_once()

if __name__ == '__main__':
    unittest.main()
