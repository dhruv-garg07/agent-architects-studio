"""
Answer Generator - Final synthesis from retrieved atomic contexts

Paper Reference: Section 3.3 - Reconstructive Synthesis (Read Path)
Generates answers from the final context C_final synthesized by query-aware retrieval
"""
from typing import List
from SimpleMem.models.memory_entry import MemoryEntry
from SimpleMem.utils.llm_client import LLMClient
from SimpleMem.config_loader import USE_JSON_FORMAT


class AnswerGenerator:
    """
    Answer Generator - Reconstructive Synthesis from Atomic Contexts

    Paper Reference: Section 3.3 - Eq. (10)
    Synthesizes final answer from pruned, query-specific context:
    C_final = ⊕_{m ∈ Top-k_dyn(S)} [t_m: Content(m)]

    Features:
    1. Receive query and retrieved atomic entries
    2. Generate answers from disambiguated, self-contained facts
    3. Ensure accuracy through atomic context independence
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def generate_answer(self, query: str, contexts: List[MemoryEntry], system_prompt: str = None) -> str:
        """
        Generate answer

        Args:
        - query: User question
        - contexts: List of retrieved relevant MemoryEntry
        - system_prompt: Optional custom system prompt overriding default behavior

        Returns:
        - Generated answer
        """
        # Build prompt and system instruction depending on context availability
        if contexts:
            context_str = self._format_contexts(contexts)
            prompt = self._build_answer_prompt(query, context_str, system_prompt)
            
            if system_prompt:
                system_instruction = system_prompt
            else:
                # Legacy fallback
                is_complex = len(query.split()) > 15
                if is_complex:
                    system_instruction = (
                        "You are a professional Q&A assistant. Extract a detailed, synthesized, "
                        "and comprehensive explanation from the context addressing all parts of the question thoroughly. "
                        "You must output valid JSON format."
                    )
                else:
                    system_instruction = "You are a professional Q&A assistant. Extract concise answers from context. You must output valid JSON format."
        else:
            # Friendly conversational fallback when no memories are retrieved
            prompt = f"""
            Respond to the user's message directly, friendly, and naturally.
            
            User Message: {query}
            
            Requirements:
            1. First, think through the reasoning process.
            2. Provide a natural, conversational, and friendly response.
            3. Return your response in JSON format.
            
            Output Format:
            ```json
            {{
              "reasoning": "Brief explanation of your response strategy",
              "answer": "Friendly and natural response"
            }}
            ```
            
            Return ONLY the JSON, no other text.
            """
            if system_prompt:
                system_instruction = system_prompt
            else:
                system_instruction = "You are a helpful, friendly, and natural AI assistant. You must output valid JSON format."

        # Ensure JSON requirement is met if not explicitly stated by custom prompt
        if system_prompt and "json" not in system_instruction.lower():
            system_instruction += " You must output valid JSON format."

        # Call LLM to generate answer
        messages = [
            {
                "role": "system",
                "content": system_instruction
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Retry up to 3 times
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use JSON format if configured
                response_format = None
                if USE_JSON_FORMAT:
                    response_format = {"type": "json_object"}

                response = self.llm_client.chat_completion(
                    messages,
                    temperature=0.1,
                    response_format=response_format
                )

                # Parse JSON response
                result = self.llm_client.extract_json(response)
                # Return the answer from JSON
                return result.get("answer", response.strip())

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Answer generation attempt {attempt + 1}/{max_retries} failed: {e}. Retrying...")
                else:
                    print(f"Warning: Failed to parse JSON response after {max_retries} attempts: {e}")
                    # Fallback to raw response
                    if 'response' in locals():
                        return response.strip()
                    else:
                        return "Failed to generate answer"

    def _format_contexts(self, contexts: List[MemoryEntry]) -> str:
        """
        Format contexts to readable text
        """
        formatted = []
        for i, entry in enumerate(contexts, 1):
            parts = [f"[Context {i}]"]
            parts.append(f"Content: {entry.lossless_restatement}")

            if entry.timestamp:
                parts.append(f"Time: {entry.timestamp}")

            if entry.location:
                parts.append(f"Location: {entry.location}")

            if entry.persons:
                parts.append(f"Persons: {', '.join(entry.persons)}")

            if entry.entities:
                parts.append(f"Related Entities: {', '.join(entry.entities)}")

            if entry.topic:
                parts.append(f"Topic: {entry.topic}")

            formatted.append("\n".join(parts))

        return "\n\n".join(formatted)

    def _build_answer_prompt(self, query: str, context_str: str, system_prompt: str = None) -> str:
        """
        Build answer generation prompt
        """
        is_chat = system_prompt and ("conversational" in system_prompt.lower() or "chat" in system_prompt.lower())
        is_complex = len(query.split()) > 15
        
        if is_chat:
            answer_requirement = (
                "Provide a natural, conversational response. Use the provided context to inform your answer. "
                "If the context is irrelevant or missing, use your general knowledge, but clearly state what you recall from memory versus general knowledge."
            )
            answer_format_example = "A friendly and helpful conversational response."
            constraint_3 = "Use the provided context to inform your answer, but you can rely on general knowledge if needed."
        else:
            answer_requirement = (
                "Then provide a detailed, synthesized, and comprehensive answer "
                "that addresses all parts and questions within the query thoroughly using the context"
                if is_complex else
                "Then provide a very CONCISE answer (short phrase about core information)"
            )
            answer_format_example = (
                "Detailed complete explanation addressing all parts of the complex query thoroughly"
                if is_complex else
                "Concise answer in a short phrase"
            )
            constraint_3 = "Answer must be based ONLY on the provided context"

        return f"""
Answer the user's question based on the provided context.

User Question: {query}

Relevant Context:
{context_str}

Requirements:
1. First, think through the reasoning process
2. {answer_requirement}
3. {constraint_3}
4. All dates in the response must be formatted as 'DD Month YYYY' but you can output more or less details if needed
5. The 'answer' field in the JSON MUST be a plain text string, NOT a nested JSON object or dictionary
6. Return your response in JSON format

Output Format:
```json
{{
  "reasoning": "Brief explanation of your thought process",
  "answer": "{answer_format_example}"
}}
```

Example:
Question: "When will they meet?"
Context: "Alice suggested meeting Bob at 2025-11-16T14:00:00..."

Output:
```json
{{
  "reasoning": "The context explicitly states the meeting time as 2025-11-16T14:00:00",
  "answer": "16 November 2025 at 2:00 PM"
}}
```

Now answer the question. Return ONLY the JSON, no other text.
"""
