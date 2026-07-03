"""
Document Synthesizer — Late Enrichment for RAG.

Synthesizes multiple document chunks into a coherent answer or context summary
using exactly ONE lightweight LLM call.
"""
from typing import List, Dict, Any
from SimpleMem.utils.llm_client import LLMClient
import logging

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT_TEMPLATE = """You are an expert AI assistant tasked with synthesizing information.
Given the user query and the retrieved document chunks, provide a comprehensive, accurate, and concise answer.
If the chunks do not contain enough information to fully answer the query, state that clearly.

--- User Query ---
{query}

--- Retrieved Document Chunks ---
{context}

--- Instructions ---
1. Synthesize the context to directly answer the user's query.
2. Rely ONLY on the provided document chunks.
3. Keep your response concise and structured.
"""

class DocumentSynthesizer:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def synthesize(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Synthesize a final response from the given query and chunks.
        Makes exactly one LLM call.
        """
        if not chunks:
            return "No relevant documents found to answer the query."

        # Format context
        context_parts = []
        for i, chunk in enumerate(chunks):
            text = chunk.get('text', '')
            meta = chunk.get('metadata', {})
            title = meta.get('title', f"Chunk {i+1}")
            context_parts.append(f"[Document: {title}]\n{text}")
            
        context_str = "\n\n".join(context_parts)
        
        prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
            query=query,
            context=context_str
        )
        
        try:
            logger.info("Calling LLM for document synthesis (1 call)...")
            # Using llm_client.generate or direct call based on client signature
            # Assuming llm_client has a standard completion/chat method
            if hasattr(self.llm_client, 'chat_completion'):
                messages = [{"role": "user", "content": prompt}]
                response = self.llm_client.chat_completion(messages=messages, temperature=0.1)
                return response
            elif hasattr(self.llm_client, 'generate'):
                return self.llm_client.generate(prompt=prompt, temperature=0.1)
            else:
                # Fallback
                messages = [{"role": "user", "content": prompt}]
                response = self.llm_client.chat_completion(messages=messages, temperature=0.1)
                return response
        except Exception as e:
            logger.error(f"Error during document synthesis: {e}")
            return f"Error synthesizing context: {e}"
