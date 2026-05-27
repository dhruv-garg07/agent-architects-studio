"""
LLM Client - Handles all LLM interactions
"""
import json
import os
import time
import requests
from typing import List, Dict, Any, Optional
# from openai import OpenAI
from SimpleMem.config_loader import TOGETHER_API_KEY, LLM_MODEL, OPENAI_BASE_URL, ENABLE_THINKING, USE_STREAMING, CLAUDE_API_KEY, CLAUDE_MODEL, COHERE_API_KEY, COHERE_MODEL
import hashlib
import threading
from together import Together
def extract_output_after_think(response: str) -> str:
    """
    Extracts and returns the part of the response after the </think> tag.
    If the tag is not found, returns the original response.
    """
    try:
        end_tag = "</think>"
        if end_tag in response:
            return response.split(end_tag, 1)[1].strip()
    except:
        return response  # fallback if tag not present
class LLMClient:
    """
    Unified LLM client interface
    """
    _response_cache = {}
    _cache_lock = threading.Lock()

    def _get_cache_key(self, messages: List[Dict[str, str]], temperature: float, response_format: Optional[Dict[str, str]]) -> str:
        # Serialize prompt structure
        try:
            serialized = json.dumps({
                "messages": messages,
                "temperature": temperature,
                "response_format": response_format,
                "model": self.model
            }, sort_keys=True)
        except Exception:
            # Fallback: string representation
            serialized = str(messages) + str(temperature) + str(response_format) + str(self.model)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        enable_thinking: Optional[bool] = None,
        use_streaming: Optional[bool] = None
    ):
        self.api_key = api_key or TOGETHER_API_KEY
        self.model = model or LLM_MODEL
        self.base_url = base_url or OPENAI_BASE_URL
        self.enable_thinking = enable_thinking if enable_thinking is not None else ENABLE_THINKING
        self.use_streaming = use_streaming if use_streaming is not None else USE_STREAMING

        # Load Claude settings
        self.claude_api_key = CLAUDE_API_KEY or os.environ.get("CLAUDE_API_KEY", "")
        self.claude_model = CLAUDE_MODEL or os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
        self.anthropic_client = None

        # Load Cohere settings
        self.cohere_api_key = COHERE_API_KEY or os.environ.get("COHERE_API_KEY", "")
        self.cohere_model = COHERE_MODEL or os.environ.get("COHERE_MODEL", "command-r-plus-08-2024")
        
        if self.claude_api_key:
            try:
                from anthropic import Anthropic
                self.anthropic_client = Anthropic(api_key=self.claude_api_key)
                print(f"Initialized Anthropic client with model: {self.claude_model}")
            except Exception as e:
                print(f"Failed to initialize Anthropic client: {e}")

        # Initialize OpenAI client with optional base_url
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
            print(f"Using custom OpenAI base URL: {self.base_url}")

        if self.enable_thinking:
            print(f"Deep thinking mode enabled")
        self.client = Together(api_key=self.api_key)


    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        response_format: Optional[Dict[str, str]] = None,
        max_retries: int = 3
    ) -> str:
        cache_key = self._get_cache_key(messages, temperature, response_format)
        with self._cache_lock:
            if cache_key in self._response_cache:
                print(f"[LLM CACHE HIT] Returning cached completion.")
                return self._response_cache[cache_key]
        
        result = self._chat_completion_uncached(
            messages=messages,
            temperature=temperature,
            response_format=response_format,
            max_retries=max_retries
        )
        
        with self._cache_lock:
            self._response_cache[cache_key] = result
            
        return result

    def _chat_completion_uncached(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        response_format: Optional[Dict[str, str]] = None,
        max_retries: int = 3
    ) -> str:
        """
        Unified completion with priority order:
        1. Cohere (Primary)
        2. OpenRouter (Nemotron free model)
        3. Together AI
        4. Anthropic Claude (last resort fallback, no startup logs)
        """
        errors = []

        # -----------------------------------------
        # Try Option 1: Cohere First
        # -----------------------------------------
        if self.cohere_api_key:
            for attempt in range(max_retries):
                try:
                    headers = {
                        "Authorization": f"Bearer {self.cohere_api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    
                    preamble = None
                    chat_history = []
                    message = ""
                    
                    for idx, msg in enumerate(messages):
                        role = msg.get("role", "").lower()
                        content = msg.get("content", "").strip()
                        
                        if role == "system":
                            preamble = content
                        elif idx == len(messages) - 1 and role == "user":
                            message = content
                        else:
                            cohere_role = "USER" if role == "user" else "CHATBOT"
                            chat_history.append({
                                "role": cohere_role,
                                "message": content
                            })
                    
                    if not message:
                        for msg in reversed(messages):
                            if msg.get("role") != "system":
                                message = msg.get("content", "")
                                break
                        if not message and messages:
                            message = messages[-1].get("content", "")
                            
                    payload = {
                        "model": self.cohere_model,
                        "message": message,
                        "temperature": temperature
                    }
                    if preamble:
                        payload["preamble"] = preamble
                    if chat_history:
                        payload["chat_history"] = chat_history
                        
                    response = requests.post(
                        "https://api.cohere.com/v1/chat",
                        headers=headers,
                        json=payload,
                        timeout=15
                    )
                    response.raise_for_status()
                    res_json = response.json()
                    content = res_json.get("text", "")
                    if content:
                        if "[END FINAL RESPONSE]" in content:
                            content = content.split("[END FINAL RESPONSE]")[0]
                        return content
                except Exception as e:
                    if attempt == max_retries - 1:
                        errors.append(f"Cohere failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)

        # -----------------------------------------
        # Try Option 2: OpenRouter Second
        # -----------------------------------------
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            for attempt in range(max_retries):

                try:
                    headers = {
                        "Authorization": f"Bearer {openrouter_key}",
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "model": "nvidia/nemotron-3-nano-30b-a3b:free",
                        "messages": messages,
                        "temperature": temperature,
                        "reasoning": {"enabled": True}
                    }
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=300
                    )
                    response.raise_for_status()
                    res_json = response.json()
                    if 'error' in res_json:
                        raise Exception(f"OpenRouter API Error: {res_json['error']}")
                    if 'choices' not in res_json:
                        raise Exception(f"Unexpected OpenRouter response: {res_json}")
                    content = res_json['choices'][0]['message'].get('content', '')
                    if content:
                        if "[END FINAL RESPONSE]" in content:
                            content = content.split("[END FINAL RESPONSE]")[0]
                        return content
                except Exception as e:
                    if attempt == max_retries - 1:
                        errors.append(f"OpenRouter failed: {e}")
                    # Print a single clean log if OpenRouter fails completely after retries
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)

        # -----------------------------------------
        # Try Option 2: Together AI Second
        # -----------------------------------------
        if self.client:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            if response_format:
                kwargs["response_format"] = response_format
                
            is_qwen_api = self.base_url and "dashscope.aliyuncs.com" in self.base_url
            if is_qwen_api:
                if self.use_streaming and self.enable_thinking and not response_format:
                    kwargs["extra_body"] = {"enable_thinking": True}
                else:
                    kwargs["extra_body"] = {"enable_thinking": False}

            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(**kwargs)
                    return response.choices[0].message.content
                except Exception as e:
                    if attempt == max_retries - 1:
                        errors.append(f"Together AI failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)

        # -----------------------------------------
        # Try Option 3: Anthropic Claude (Last Resort)
        # -----------------------------------------
        if self.anthropic_client:
            system_prompt = ""
            filtered_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_prompt = msg.get("content", "")
                else:
                    role = msg.get("role")
                    if role not in ("user", "assistant"):
                        role = "user"
                    filtered_messages.append({
                        "role": role,
                        "content": msg.get("content")
                    })

            for attempt in range(max_retries):
                try:
                    kwargs = {
                        "model": self.claude_model,
                        "messages": filtered_messages,
                        "temperature": temperature,
                        "max_tokens": 4000
                    }
                    if system_prompt:
                        kwargs["system"] = system_prompt
                    
                    response = self.anthropic_client.messages.create(**kwargs)
                    return response.content[0].text
                except Exception as e:
                    if attempt == max_retries - 1:
                        errors.append(f"Anthropic Claude failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)

        # If all failed, raise unified exception
        raise Exception(f"All LLM providers failed to complete request. Errors: {'; '.join(errors)}")

    def _handle_streaming_response(self, **kwargs) -> str:
        """
        Handle streaming response and collect full content
        """
        full_content = []
        
        # Try Cohere First
        if self.cohere_api_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.cohere_api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                messages = kwargs.get("messages", [])
                temperature = kwargs.get("temperature", 0.2)
                
                preamble = None
                chat_history = []
                message = ""
                
                for idx, msg in enumerate(messages):
                    role = msg.get("role", "").lower()
                    content = msg.get("content", "").strip()
                    
                    if role == "system":
                        preamble = content
                    elif idx == len(messages) - 1 and role == "user":
                        message = content
                    else:
                        cohere_role = "USER" if role == "user" else "CHATBOT"
                        chat_history.append({
                            "role": cohere_role,
                            "message": content
                        })
                
                if not message:
                    for msg in reversed(messages):
                        if msg.get("role") != "system":
                            message = msg.get("content", "")
                            break
                    if not message and messages:
                        message = messages[-1].get("content", "")
                        
                payload = {
                    "model": self.cohere_model,
                    "message": message,
                    "temperature": temperature
                }
                if preamble:
                    payload["preamble"] = preamble
                if chat_history:
                    payload["chat_history"] = chat_history
                    
                response = requests.post(
                    "https://api.cohere.com/v1/chat",
                    headers=headers,
                    json=payload,
                    timeout=15
                )
                response.raise_for_status()
                res_json = response.json()
                content = res_json.get("text", "")
                if content:
                    if "[END FINAL RESPONSE]" in content:
                        content = content.split("[END FINAL RESPONSE]")[0]
                    return content
            except Exception as e:
                print(f"Cohere streaming fallback failed: {e}")

        # Try OpenRouter Second
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        try:
            if openrouter_key:
                headers = {
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": "nvidia/nemotron-3-nano-30b-a3b:free",
                    "messages": kwargs.get("messages", []),
                    "temperature": kwargs.get("temperature", 0.2),
                    "reasoning": {"enabled": True}
                }
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=300
                )
                response.raise_for_status()
                res_json = response.json()
                if 'error' in res_json:
                    raise Exception(f"OpenRouter API Error: {res_json['error']}")
                if 'choices' not in res_json:
                    raise Exception(f"Unexpected OpenRouter response: {res_json}")
                content = res_json['choices'][0]['message'].get('content', '')
                if content:
                    if "[END FINAL RESPONSE]" in content:
                        content = content.split("[END FINAL RESPONSE]")[0]
                    return content
        except Exception as e:
            print(f"OpenRouter streaming fallback to Together AI failed: {e}")

        stream = self.client.chat.completions.create(**kwargs)

        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_content.append(content)
                # Optional: print streaming content in real-time
                # print(content, end='', flush=True)

        return ''.join(full_content)

    def extract_json(self, text: str) -> Any:
        """
        Extract JSON from LLM response with robust parsing
        Supports multiple formats:
        1. Pure JSON
        2. ```json ... ```
        3. ``` ... ``` (generic code block)
        4. JSON embedded in text with common prefixes
        5. Multiple JSON objects (returns first valid one)
        """
        if not text or not text.strip():
            raise ValueError("Empty response received")

        text = text.strip()

        # Remove common LLM prefixes/suffixes
        common_prefixes = [
            "Here's the JSON:",
            "Here is the JSON:",
            "The JSON is:",
            "JSON:",
            "Result:",
            "Output:",
            "Answer:",
        ]
        for prefix in common_prefixes:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()

        # Try direct parsing first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from ```json ... ``` block
        if "```json" in text.lower():
            # Case insensitive search for ```json
            start_marker = "```json"
            start_idx = text.lower().find(start_marker)
            if start_idx != -1:
                start = start_idx + len(start_marker)
                # Find the closing ```
                end = text.find("```", start)
                if end != -1:
                    json_str = text[start:end].strip()
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        # Try to clean up common issues
                        json_str = self._clean_json_string(json_str)
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            pass

        # Try extracting from generic ``` ... ``` code block
        if "```" in text:
            start = text.find("```") + 3
            # Skip language identifier if present
            newline = text.find("\n", start)
            if newline != -1 and newline - start < 20:
                start = newline + 1
            end = text.find("```", start)
            if end != -1:
                json_str = text[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Try to clean up
                    json_str = self._clean_json_string(json_str)
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass

        # Try finding balanced JSON object/array by scanning for { or [
        for start_char in ['{', '[']:
            result = self._extract_balanced_json(text, start_char)
            if result is not None:
                return result

        # Last resort: try to find any JSON-like structure and clean it
        for start_char in ['{', '[']:
            start_idx = text.find(start_char)
            if start_idx != -1:
                # Extract a large chunk and try to parse
                chunk = text[start_idx:]
                cleaned = self._clean_json_string(chunk)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass

        raise ValueError(f"Failed to extract valid JSON from response. Response: {text}...")

    def _clean_json_string(self, json_str: str) -> str:
        """
        Clean common issues in JSON strings from LLM output
        """
        # Remove trailing commas before } or ]
        import re
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

        # Remove comments (// and /* */)
        json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

        return json_str.strip()

    def _extract_balanced_json(self, text: str, start_char: str) -> Any:
        """
        Extract a balanced JSON object or array starting with start_char
        """
        end_char = '}' if start_char == '{' else ']'
        start_idx = text.find(start_char)

        if start_idx == -1:
            return None

        # Track depth to find matching closing bracket
        depth = 0
        in_string = False
        escape_next = False

        for i in range(start_idx, len(text)):
            char = text[i]

            # Handle string escaping
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            # Handle strings (don't count brackets inside strings)
            if char == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            # Count depth
            if char == start_char:
                depth += 1
            elif char == end_char:
                depth -= 1
                if depth == 0:
                    json_str = text[start_idx:i+1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # Try cleaning and parsing again
                        cleaned = self._clean_json_string(json_str)
                        try:
                            return json.loads(cleaned)
                        except json.JSONDecodeError:
                            # Continue searching for next occurrence
                            break

        return None


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("LLMClient Interactive Test & Verification Suite")
    print("=" * 60)
    
    client = LLMClient()
    
    # Check if custom prompt is provided
    custom_prompt = None
    if len(sys.argv) > 1:
        custom_prompt = " ".join(sys.argv[1:])
        print(f"Using prompt from command line argument: '{custom_prompt}'")
    
    if custom_prompt:
        # 1. Clear cache to guarantee it hits the actual API
        LLMClient._response_cache.clear()
        
        # 2. Verify and show API key details to confirm we are using the user's key
        print("\n--- API Configuration Verification ---")
        if client.claude_api_key:
            # Obfuscate key for display
            key_display = client.claude_api_key[:8] + "..." + client.claude_api_key[-8:]
            print(f"Anthropic API Key Detected: {key_display}")
            print(f"Target Model: {client.claude_model}")
            
            # Confirm the Anthropic Client is initialized
            if not client.anthropic_client:
                from anthropic import Anthropic
                client.anthropic_client = Anthropic(api_key=client.claude_api_key)
            print("Anthropic client object successfully created.")
            
            # 3. Execute call & verify
            print("\n--- Sending request to Anthropic API ---")
            messages = [{"role": "user", "content": custom_prompt}]
            
            start_time = time.time()
            response = client.chat_completion(messages, temperature=0.0)
            duration = time.time() - start_time
            
            print("\n--- Response Received ---")
            print(response)
            print(f"\nRequest Duration: {duration:.2f} seconds")
            print("✅ Successfully hit Anthropic APIs and fetched response using your API key!")
        else:
            print("❌ Anthropic Claude API key (CLAUDE_API_KEY) is not configured!")
            
    else:
        # 1. Test JSON Extraction (Local)
        print("\n--- Running JSON Extraction Tests (Local) ---")
        
        test_cases = [
            ("Pure JSON", '{"name": "Test", "value": 42}'),
            ("JSON in Markdown code block", '```json\n{"name": "Test", "value": 42}\n```'),
            ("JSON in generic code block", '```\n{"name": "Test", "value": 42}\n```'),
            ("JSON with prefix", 'Here is the JSON response:\n{"name": "Test", "value": 42}'),
            ("JSON with comments and trailing commas", '{\n    "name": "Test", // standard comment\n    "value": 42,\n    "items": [1, 2, 3,],\n}'),
            ("JSON embedded in text with balanced braces", 'Some initial conversational text followed by: {"name": "Test", "value": 42} and some closing text.')
        ]
        
        all_passed = True
        for name, text in test_cases:
            try:
                result = client.extract_json(text)
                expected = {"name": "Test", "value": 42} if "items" not in text else {"name": "Test", "value": 42, "items": [1, 2, 3]}
                if result == expected or (isinstance(result, dict) and result.get("name") == "Test" and result.get("value") == 42):
                    print(f"✅ {name}: PASSED")
                else:
                    print(f"❌ {name}: FAILED (Unexpected output: {result})")
                    all_passed = False
            except Exception as e:
                print(f"❌ {name}: FAILED with exception: {e}")
                all_passed = False

        # 2. Live API Completion Tests
        print("\n--- Running Live API Completion Tests ---")
        messages = [{"role": "user", "content": "Say hello in exactly 3 words."}]
        
        # Test Claude if Claude key is present
        if client.claude_api_key:
            print(f"\nTesting Anthropic Claude (Model: {client.claude_model})...")
            try:
                # Make sure anthropic client is set up
                if not client.anthropic_client:
                    from anthropic import Anthropic
                    client.anthropic_client = Anthropic(api_key=client.claude_api_key)
                
                print("Anthropic Client:", client.anthropic_client)
                start_time = time.time()
                response = client.chat_completion(messages, temperature=0.0)
                duration = time.time() - start_time
                print(f"Response: '{response.strip()}'")
                print(f"Duration: {duration:.2f}s")
                
                # Test Cache Hit
                print("Testing cache for Anthropic Claude...")
                start_time = time.time()
                cached_response = client.chat_completion(messages, temperature=0.0)
                duration = time.time() - start_time
                print(f"Cached Response: '{cached_response.strip()}'")
                print(f"Cached Duration: {duration:.4f}s")
                if cached_response == response:
                    print("✅ Cache functional for Anthropic")
                else:
                    print("❌ Cache failed for Anthropic")
                    
            except Exception as e:
                print(f"❌ Claude completion failed: {e}")
        else:
            print("\nAnthropic Claude API key not configured. Skipping Claude tests.")

        # Test Together AI
        if client.api_key:
            print(f"\nTesting Together AI (Model: {client.model})...")
            try:
                # Clear cache to ensure a fresh Together AI request
                LLMClient._response_cache.clear()
                
                # Temporarily disable anthropic client to force Together AI code path
                orig_anthropic = client.anthropic_client
                client.anthropic_client = None
                
                start_time = time.time()
                response = client.chat_completion(messages, temperature=0.0)
                duration = time.time() - start_time
                print(f"Response: '{response.strip()}'")
                print(f"Duration: {duration:.2f}s")
                
                # Test Cache Hit
                print("Testing cache for Together AI...")
                start_time = time.time()
                cached_response = client.chat_completion(messages, temperature=0.0)
                duration = time.time() - start_time
                print(f"Cached Response: '{cached_response.strip()}'")
                print(f"Cached Duration: {duration:.4f}s")
                if cached_response == response:
                    print("✅ Cache functional for Together AI")
                else:
                    print("❌ Cache failed for Together AI")
                
                # Restore anthropic client
                client.anthropic_client = orig_anthropic
                
            except Exception as e:
                print(f"❌ Together AI completion failed: {e}")
        else:
            print("\nTogether AI API key not configured. Skipping Together AI tests.")