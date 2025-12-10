import re
import json
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter, defaultdict
import random
from datetime import datetime

class AdvancedQueryRewriter:
    """Advanced query rewriting engine with multiple strategies"""
    
    def __init__(self):
        # Query patterns for different intents
        self.intent_patterns = {
            "definition": [
                r"what (?:is|are) (?:a |an |the )?([\w\s]+)\?",
                r"define ([\w\s]+)",
                r"meaning of ([\w\s]+)"
            ],
            "comparison": [
                r"compare ([\w\s]+) (?:and|with|to) ([\w\s]+)",
                r"difference between ([\w\s]+) (?:and|&) ([\w\s]+)",
                r"(?:how is|what makes) ([\w\s]+) different from ([\w\s]+)"
            ],
            "procedure": [
                r"how (?:to|do I|can I) ([\w\s]+)",
                r"steps to ([\w\s]+)",
                r"process of ([\w\s]+)",
                r"method (?:for|to) ([\w\s]+)"
            ],
            "explanation": [
                r"explain ([\w\s]+)",
                r"tell me about ([\w\s]+)",
                r"describe ([\w\s]+)",
                r"what (?:does|do) ([\w\s]+) (?:mean|refer to)"
            ],
            "analysis": [
                r"analyze ([\w\s]+)",
                r"break down ([\w\s]+)",
                r"evaluate ([\w\s]+)",
                r"critique ([\w\s]+)"
            ]
        }
        
        # Stop words for query optimization
        self.stop_words = {
            'the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'on', 'with', 'as', 'by',
            'an', 'at', 'from', 'this', 'that', 'it', 'be', 'are', 'was', 'were', 'or',
            'but', 'not', 'have', 'has', 'had', 'can', 'will', 'would', 'should', 'could',
            'tell', 'me', 'about', 'explain', 'describe', 'what', 'how', 'why', 'when',
            'where', 'which', 'who', 'whom', 'whose', 'please', 'kindly', 'could you',
            'would you', 'can you', 'i need', 'i want', 'help me', 'assist me'
        }
        
        # Academic/technical stop phrases
        self.stop_phrases = [
            "i would like to know",
            "can you tell me",
            "could you explain",
            "i need help with",
            "please provide",
            "give me information about",
            "looking for information on",
            "seeking clarification on"
        ]
        
        # Query expansion patterns
        self.expansion_patterns = {
            "acronym": lambda term: [f"{term} definition", f"{term} meaning", f"what is {term}"],
            "concept": lambda term: [f"{term} explanation", f"{term} overview", f"understanding {term}"],
            "process": lambda term: [f"{term} steps", f"{term} procedure", f"how to {term}"],
            "comparison": lambda term: [f"{term} vs", f"{term} comparison", f"{term} differences"]
        }
        
        # Cache for rewritten queries
        self.query_cache = {}
        self.cache_size = 1000
        
    def intelligent_query_rewriter(
        self,
        original_query: str,
        context: str = "",
        key_concepts: List[str] = None,
        mode: str = "balanced",
        rag_context: List[Dict] = None,
        chat_history: List[Dict] = None
    ) -> str:
        """
        Advanced query rewriting with multiple strategies.
        
        Args:
            original_query: User's original query
            context: Additional context for rewriting
            key_concepts: Important concepts to emphasize
            mode: Rewriting mode ('precise', 'balanced', 'creative', 'expansive')
            rag_context: Previous RAG results for context
            chat_history: Chat history for contextual understanding
            
        Returns:
            Rewritten, optimized query
        """
        print(f"🔧 [Query Rewriter] Mode: {mode} | Original: '{original_query[:50]}...'")
        
        # Step 1: Check cache first
        cache_key = self._generate_cache_key(original_query, context, key_concepts, mode)
        if cache_key in self.query_cache:
            print(f"  ↳ Cache hit for query")
            return self.query_cache[cache_key]
        
        # Step 2: Pre-process query
        cleaned_query = self._preprocess_query(original_query)
        
        # Step 3: Detect query intent
        intent, extracted_entities = self._detect_intent_and_entities(cleaned_query)
        print(f"  ↳ Detected intent: {intent} | Entities: {extracted_entities}")
        
        # Step 4: Extract key terms from multiple sources
        all_key_terms = self._extract_key_terms(
            query=cleaned_query,
            context=context,
            key_concepts=key_concepts or [],
            rag_context=rag_context,
            chat_history=chat_history,
            intent=intent
        )
        
        # Step 5: Apply rewriting strategy based on mode
        if mode == "precise":
            rewritten = self._precise_rewrite(cleaned_query, all_key_terms, intent, extracted_entities)
        elif mode == "creative":
            rewritten = self._creative_rewrite(cleaned_query, all_key_terms, intent, extracted_entities)
        elif mode == "expansive":
            rewritten = self._expansive_rewrite(cleaned_query, all_key_terms, intent, extracted_entities)
        else:  # balanced
            rewritten = self._balanced_rewrite(cleaned_query, all_key_terms, intent, extracted_entities)
        
        # Step 6: Apply query optimization
        optimized = self._optimize_query(rewritten, mode)
        
        # Step 7: Add context hints if needed
        if context and len(optimized.split()) < 8:
            optimized = self._add_context_hints(optimized, all_key_terms)
        
        # Step 8: Validate and finalize
        final_query = self._validate_query(optimized, original_query)
        
        # Step 9: Cache the result
        self._update_cache(cache_key, final_query)
        
        print(f"  ↳ Rewritten: '{final_query}'")
        print(f"  ↳ Length: {len(original_query)} → {len(final_query)} chars")
        
        return final_query
    
    def _generate_cache_key(self, query: str, context: str, key_concepts: List[str], mode: str) -> str:
        """Generate unique cache key for query"""
        components = [
            query.lower().strip(),
            context.lower().strip()[:100],
            json.dumps(sorted(key_concepts or [])),
            mode
        ]
        key_string = "||".join(components)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _update_cache(self, key: str, value: str):
        """Update query cache with LRU-like behavior"""
        if len(self.query_cache) >= self.cache_size:
            # Remove oldest entry (simple strategy)
            oldest_key = next(iter(self.query_cache))
            del self.query_cache[oldest_key]
        
        self.query_cache[key] = value
    
    def _preprocess_query(self, query: str) -> str:
        """Clean and normalize the query"""
        query = query.strip()
        
        # Remove excessive punctuation
        query = re.sub(r'[!?]{2,}', '?', query)
        
        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query)
        
        # Fix common typos
        common_typos = {
            'wierd': 'weird',
            'recieve': 'receive',
            'seperate': 'separate',
            'occured': 'occurred',
            'definately': 'definitely',
            'goverment': 'government'
        }
        
        for typo, correction in common_typos.items():
            query = re.sub(rf'\b{typo}\b', correction, query, flags=re.IGNORECASE)
        
        return query
    
    def _detect_intent_and_entities(self, query: str) -> Tuple[str, List[str]]:
        """Detect query intent and extract entities"""
        query_lower = query.lower()
        
        # Check for intent patterns
        detected_intent = "general"
        entities = []
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, query_lower)
                if matches:
                    detected_intent = intent
                    # Flatten matches and extract entities
                    for match in matches:
                        if isinstance(match, tuple):
                            entities.extend([m.strip() for m in match if m.strip()])
                        elif isinstance(match, str):
                            entities.append(match.strip())
                    break
            if detected_intent != "general":
                break
        
        # Extract additional entities using NLP-like patterns
        # Proper nouns (capitalized phrases)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        entities.extend(proper_nouns)
        
        # Technical terms (words with specific suffixes)
        technical_suffixes = ['tion', 'ism', 'ity', 'ment', 'ology', 'ics', 'ing']
        for suffix in technical_suffixes:
            tech_terms = re.findall(rf'\b\w*{suffix}\b', query, re.IGNORECASE)
            entities.extend(tech_terms)
        
        # Remove duplicates and empty strings
        entities = list(dict.fromkeys([e for e in entities if e]))
        
        return detected_intent, entities
    
    def _extract_key_terms(
        self,
        query: str,
        context: str,
        key_concepts: List[str],
        rag_context: List[Dict],
        chat_history: List[Dict],
        intent: str
    ) -> Dict[str, float]:
        """Extract and score key terms from multiple sources"""
        term_scores = defaultdict(float)
        
        # 1. Extract from query
        query_terms = self._extract_terms_from_text(query)
        for term in query_terms:
            term_scores[term] += 3.0  # Highest weight for query terms
        
        # 2. Extract from context
        if context:
            context_terms = self._extract_terms_from_text(context)
            for term in context_terms:
                term_scores[term] += 1.5
        
        # 3. Add provided key concepts
        for concept in key_concepts:
            if concept:
                term_scores[concept.lower()] += 2.0
        
        # 4. Extract from RAG context
        if rag_context:
            rag_terms = []
            for item in rag_context[:3]:  # Top 3 RAG items
                if isinstance(item, dict):
                    text = item.get('document', item.get('content', ''))
                else:
                    text = str(item)
                rag_terms.extend(self._extract_terms_from_text(text))
            
            for term in rag_terms:
                term_scores[term] += 1.0
        
        # 5. Extract from chat history (recent exchanges)
        if chat_history:
            recent_history = chat_history[-4:]  # Last 2 exchanges
            for msg in recent_history:
                if isinstance(msg, dict):
                    content = msg.get('content', '')
                    history_terms = self._extract_terms_from_text(content)
                    for term in history_terms:
                        term_scores[term] += 0.5
        
        # 6. Boost terms based on intent
        self._boost_terms_by_intent(term_scores, intent)
        
        # Remove stop words from scores
        for stop_word in self.stop_words:
            term_scores.pop(stop_word, None)
        
        return dict(term_scores)
    
    def _extract_terms_from_text(self, text: str) -> List[str]:
        """Extract meaningful terms from text"""
        if not text:
            return []
        
        # Clean text
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Tokenize
        tokens = text.split()
        
        # Remove stop words and short words
        filtered = [
            token for token in tokens
            if token not in self.stop_words and len(token) > 2
        ]
        
        # Extract bi-grams for better context
        bi_grams = []
        for i in range(len(filtered) - 1):
            bi_gram = f"{filtered[i]} {filtered[i+1]}"
            # Check if bi-gram is meaningful (not just stop word combinations)
            if filtered[i] not in self.stop_words and filtered[i+1] not in self.stop_words:
                bi_grams.append(bi_gram)
        
        return filtered + bi_grams
    
    def _boost_terms_by_intent(self, term_scores: Dict[str, float], intent: str):
        """Boost term scores based on query intent"""
        intent_boost_factors = {
            "definition": {"definition", "meaning", "what is", "explain"},
            "comparison": {"difference", "compare", "vs", "versus", "versus"},
            "procedure": {"steps", "how to", "process", "method", "procedure"},
            "analysis": {"analyze", "evaluate", "critique", "break down"},
            "explanation": {"explain", "describe", "tell", "overview"}
        }
        
        if intent in intent_boost_factors:
            boost_terms = intent_boost_factors[intent]
            for term in list(term_scores.keys()):
                if any(boost_term in term for boost_term in boost_terms):
                    term_scores[term] *= 1.5
    
    def _precise_rewrite(
        self,
        query: str,
        key_terms: Dict[str, float],
        intent: str,
        entities: List[str]
    ) -> str:
        """Precise, focused rewriting for factual queries"""
        # Sort terms by score
        sorted_terms = sorted(key_terms.items(), key=lambda x: x[1], reverse=True)
        top_terms = [term for term, score in sorted_terms[:5]]
        
        # Build concise query
        if intent == "definition":
            if entities:
                return f"definition of {entities[0]}"
            elif top_terms:
                return f"what is {top_terms[0]}"
        
        elif intent == "comparison":
            if len(entities) >= 2:
                return f"compare {entities[0]} vs {entities[1]}"
            elif len(top_terms) >= 2:
                return f"{top_terms[0]} vs {top_terms[1]} difference"
        
        # Default precise rewrite
        if top_terms:
            return " ".join(top_terms[:3])
        
        return query
    
    def _creative_rewrite(
        self,
        query: str,
        key_terms: Dict[str, float],
        intent: str,
        entities: List[str]
    ) -> str:
        """Creative, expansive rewriting for open-ended queries"""
        # Use more terms for creative exploration
        sorted_terms = sorted(key_terms.items(), key=lambda x: x[1], reverse=True)
        top_terms = [term for term, score in sorted_terms[:8]]
        
        # Add exploratory phrases
        exploratory_phrases = [
            "comprehensive analysis of",
            "in-depth exploration of",
            "detailed examination of",
            "thorough investigation into"
        ]
        
        phrase = random.choice(exploratory_phrases)
        
        if entities:
            return f"{phrase} {', '.join(entities[:2])}"
        elif top_terms:
            return f"{phrase} {', '.join(top_terms[:3])}"
        
        return f"{phrase} {query}"
    
    def _expansive_rewrite(
        self,
        query: str,
        key_terms: Dict[str, float],
        intent: str,
        entities: List[str]
    ) -> str:
        """Highly expansive rewriting with query variations"""
        # Generate multiple query variations
        variations = []
        
        # Variation 1: Original with key terms
        if key_terms:
            top_terms = sorted(key_terms.items(), key=lambda x: x[1], reverse=True)[:4]
            terms_str = " ".join([term for term, _ in top_terms])
            variations.append(f"{query} {terms_str}")
        
        # Variation 2: Question-based
        question_frameworks = [
            "What are the key aspects of {}?",
            "How does {} work in practice?",
            "What factors influence {}?",
            "What are the applications of {}?"
        ]
        
        if entities:
            for framework in question_frameworks:
                variations.append(framework.format(entities[0]))
        
        # Variation 3: Multi-perspective
        if len(entities) >= 2:
            variations.append(f"Technical and practical perspectives on {entities[0]} and {entities[1]}")
        
        # Variation 4: Contextual (if we have enough terms)
        if len(key_terms) >= 3:
            top_three = sorted(key_terms.items(), key=lambda x: x[1], reverse=True)[:3]
            context_terms = [term for term, _ in top_three]
            variations.append(f"context: {context_terms[0]} within {context_terms[1]} framework considering {context_terms[2]}")
        
        # Select best variation based on length and term coverage
        best_variation = query
        best_score = 0
        
        for variation in variations:
            score = len(variation.split()) * 0.5  # Prefer longer queries
            score += sum(1 for term in key_terms if term in variation.lower()) * 2
            
            if score > best_score:
                best_score = score
                best_variation = variation
        
        return best_variation
    
    def _balanced_rewrite(
        self,
        query: str,
        key_terms: Dict[str, float],
        intent: str,
        entities: List[str]
    ) -> str:
        """Balanced rewriting for general queries"""
        # Remove conversational phrases
        for phrase in self.stop_phrases:
            if query.lower().startswith(phrase):
                query = query[len(phrase):].strip()
                break
        
        # Add key terms if query is too short
        if len(query.split()) < 4 and key_terms:
            top_terms = sorted(key_terms.items(), key=lambda x: x[1], reverse=True)[:3]
            additional_terms = " ".join([term for term, _ in top_terms])
            
            if intent == "definition":
                return f"definition {additional_terms}"
            elif intent == "comparison":
                return f"comparison {additional_terms}"
            else:
                return f"{query} {additional_terms}"
        
        # For longer queries, refine with key entities
        if entities:
            entity_str = " ".join(entities[:2])
            if entity_str not in query.lower():
                return f"{query} {entity_str}"
        
        return query
    
    def _optimize_query(self, query: str, mode: str) -> str:
        """Optimize query for search/RAG systems"""
        # Remove redundant words
        words = query.split()
        unique_words = []
        seen_words = set()
        
        for word in words:
            word_lower = word.lower()
            if word_lower not in seen_words or word[0].isupper():  # Keep proper nouns
                unique_words.append(word)
                seen_words.add(word_lower)
        
        query = " ".join(unique_words)
        
        # Adjust length based on mode
        max_lengths = {
            "precise": 10,
            "balanced": 15,
            "creative": 20,
            "expansive": 25
        }
        
        max_len = max_lengths.get(mode, 15)
        if len(query.split()) > max_len:
            words = query.split()[:max_len]
            
            # Try to end at a complete phrase
            for i in range(len(words) - 1, 0, -1):
                if words[i] in [".", "?", ":", ";"] or words[i].endswith((".", "?", ":")):
                    words = words[:i+1]
                    break
            
            query = " ".join(words)
        
        # Ensure query ends properly
        if not query.endswith(("?", ".", "!", '"')):
            if mode in ["creative", "expansive"]:
                query += "?"
            elif any(word in query.lower() for word in ["what", "how", "why", "when", "where"]):
                query += "?"
        
        return query.strip()
    
    def _add_context_hints(self, query: str, key_terms: Dict[str, float]) -> str:
        """Add context hints to short queries"""
        if len(query.split()) >= 5:
            return query
        
        top_terms = sorted(key_terms.items(), key=lambda x: x[1], reverse=True)[:3]
        context_terms = [term for term, _ in top_terms if term not in query.lower()]
        
        if context_terms:
            # Add as parenthetical context
            context_str = " ".join(context_terms[:2])
            return f"{query} (context: {context_str})"
        
        return query
    
    def _validate_query(self, rewritten: str, original: str) -> str:
        """Validate and finalize the rewritten query"""
        if not rewritten or len(rewritten.strip()) < 3:
            print(f"  ↳ Warning: Rewritten query too short, using original")
            return original
        
        # Check if rewriting actually improved the query
        original_word_count = len(original.split())
        rewritten_word_count = len(rewritten.split())
        
        # If rewritten is significantly worse, fall back
        if rewritten_word_count < 2 and original_word_count > 3:
            return original
        
        # Check for gibberish or repeated characters
        if re.search(r'(.)\1{3,}', rewritten):  # 4+ repeated characters
            return original
        
        return rewritten.strip()


# ==================== MAIN FUNCTION ====================
# Create global instance
query_rewriter = AdvancedQueryRewriter()

def intelligent_query_rewriter(
    original_query: str,
    context: str = "",
    key_concepts: List[str] = None,
    mode: str = "balanced",
    rag_context: List[Dict] = None,
    chat_history: List[Dict] = None
) -> str:
    """
    Main function for intelligent query rewriting.
    This is the function to call from your API.
    """
    return query_rewriter.intelligent_query_rewriter(
        original_query=original_query,
        context=context,
        key_concepts=key_concepts,
        mode=mode,
        rag_context=rag_context,
        chat_history=chat_history
    )


# ==================== LLM-ENHANCED REWRITER (OPTIONAL) ====================
from together_get_response import stream_chat_response
class LLMEnhancedRewriter:
    """Optional LLM-based query rewriter for complex cases"""
    
    def __init__(self):
        self.cache = {}
        self.fallback_rewriter = AdvancedQueryRewriter()
    
    def rewrite_with_llm(
        self,
        query: str,
        context: str,
        mode: str,
        # llm_provider=stream_chat_response  # Your LLM interface
    ) -> str:
        """Use LLM for complex query rewriting when available"""
        
        # if not llm_provider:
        #     # Fallback to rule-based rewriter
        #     return self.fallback_rewriter.intelligent_query_rewriter(
        #         original_query=query,
        #         context=context,
        #         mode=mode
        #     )
        
        # Build sophisticated LLM prompt
        prompt = f"""You are an expert query optimizer for information retrieval systems.
        
        ORIGINAL QUERY: {query}
        
        CONTEXT FOR REWRITING: {context}
        
        MODE: {mode} (precise=factual/concise, balanced=mixed, creative=exploratory)
        Chunks can be irrelevant. Understand the query {query} and filter out the noise and find the keywords associated with the query only.
        Remove unnecessary chunks and their keywords.
        TASK: Extract what the user wants to get from the context:
        1. Semantic search relevance
        2. Context understanding
        3. Retrieval precision and recall
        
        GUIDELINES:
        - Preserve the core intent
        - Expand with relevant context
        - Remove conversational fluff
        - Add technical specificity
        - Consider synonyms and related concepts
        - Format as search-optimized keywords
        
        OUTPUT FORMAT: Return ONLY the chunks, keywords and the chunks and context that user wants from the given context provided., no explanations.
        
        REWRITTEN QUERY:"""
        
        try:
            # Call your LLM
            rewritten = ""
            response = stream_chat_response(prompt=prompt, temperature=0.3)
            for token in response:
                print(token, end='', flush=True)
                rewritten += token
            
            
            # Validate LLM response
            if self._validate_llm_response(rewritten, query):
                return rewritten
            
        except Exception as e:
            print(f"LLM rewriter error: {e}")
        
        # Fallback
        return self.fallback_rewriter.intelligent_query_rewriter(
            original_query=query,
            context=context,
            mode=mode
        )
    
    def _validate_llm_response(self, rewritten: str, original: str) -> bool:
        """Validate LLM-generated query"""
        if not rewritten or len(rewritten) < 3:
            return False
        
        if rewritten.lower() == original.lower():
            return False
        
        # Check for common LLM failure patterns
        failure_patterns = [
            "I cannot",
            "I'm sorry",
            "As an AI",
            "I don't understand",
            "rewritten query:",
            "here is the",
            "the rewritten query is"
        ]
        
        for pattern in failure_patterns:
            if pattern.lower() in rewritten.lower():
                return False
        
        return True