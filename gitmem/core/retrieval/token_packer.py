"""
GitMem v2.0 — Token Packer

Packs ranked memories into a context window without exceeding the token budget.
Uses a fast heuristic for token counting (1 token ~= 4 chars) or tiktoken if available.
"""

from typing import List, Dict, Any, Tuple


class TokenPacker:
    """Packs memories to fit within an LLM token budget."""
    
    def __init__(self, max_tokens: int = 4000, chars_per_token: float = 4.0):
        self.max_tokens = max_tokens
        self.chars_per_token = chars_per_token
        
        # Try to use tiktoken if installed
        try:
            import tiktoken
            self.encoding = tiktoken.get_encoding("cl100k_base")
            self.use_tiktoken = True
        except ImportError:
            self.use_tiktoken = False

    def count_tokens(self, text: str) -> int:
        """Count tokens in a string."""
        if not text:
            return 0
        if self.use_tiktoken:
            return len(self.encoding.encode(text))
        return int(len(text) / self.chars_per_token)

    def pack(self, ranked_memories: List[Dict[str, Any]], system_prompt_tokens: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """
        Packs as many memories as possible into the budget.
        Returns the packed list and total tokens used.
        """
        budget = self.max_tokens - system_prompt_tokens
        if budget <= 0:
            return [], 0
            
        packed = []
        tokens_used = 0
        
        for mem in ranked_memories:
            content = mem.get("content", "")
            # Add overhead for formatting (e.g. JSON brackets, newlines)
            tokens = self.count_tokens(content) + 10 
            
            if tokens_used + tokens <= budget:
                packed.append(mem)
                tokens_used += tokens
            else:
                # Could optionally truncate the last memory here
                break
                
        return packed, tokens_used
