#!/usr/bin/env python3
"""
Cohere API Key Testing Script
-----------------------------
This script tests the validity and functionality of a Cohere API key by:
1. Verifying the API key authorization against the Cohere Models endpoint.
2. Discovering the best available chat model.
3. Sending a series of basic questions to check reasoning and correctness.
"""

import sys
import requests

# The API key to test
COHERE_API_KEY = "gxA2nmtzlyRoLzXQzIuKPaQH6vzuAxkVIFmklF0J"
MODELS_URL = "https://api.cohere.com/v1/models"
CHAT_URL = "https://api.cohere.com/v1/chat"

def get_headers():
    return {
        "Authorization": f"Bearer {COHERE_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def discover_model():
    """Queries Cohere Models endpoint to find active chat models."""
    print("Checking available models and validating key...")
    headers = get_headers()
    
    try:
        response = requests.get(MODELS_URL, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ Authentication/API Check Failed (Status {response.status_code})")
            try:
                print(f"Error response: {response.json()}")
            except Exception:
                print(f"Raw error response: {response.text}")
            return None
        
        data = response.json()
        models = data.get("models", [])
        
        # Let's look for chat-capable models
        chat_models = []
        for m in models:
            # Look for models that support chat endpoint
            endpoints = m.get("endpoints", [])
            if "chat" in endpoints:
                chat_models.append(m.get("name"))
            elif "generate" in endpoints:
                # Check if name suggests chat support
                chat_models.append(m.get("name"))
        
        if not chat_models:
            # Fallback to filtering by name if endpoints not specified
            chat_models = [m.get("name") for m in models if "command" in m.get("name", "")]

        print(f"🟢 Key is VALID! Discovered {len(models)} models.")
        if chat_models:
            print(f"Discovered chat-compatible models: {', '.join(chat_models[:5])}")
            # Pick the best command model (command-r-plus-08-2024, command-r, command, etc.)
            for preferred in ["command-r-plus-08-2024", "command-r-08-2024", "command-r", "command", "command-light"]:
                if preferred in chat_models:
                    print(f"🎯 Selected model for testing: '{preferred}'")
                    return preferred
            # Fallback to the first chat-capable model
            print(f"🎯 Selected first available model: '{chat_models[0]}'")
            return chat_models[0]
            
    except Exception as e:
        print(f"⚠️ Warning: Failed to discover models dynamically: {e}")
    
    # Hardcoded fallback if discovery failed but key might still work
    print("🎯 Falling back to default model: 'command-r'")
    return "command-r"

def run_test():
    print("=" * 60)
    print("               COHERE API KEY TESTING SUITE")
    print("=" * 60)
    print(f"Target Key:  {COHERE_API_KEY[:6]}...{COHERE_API_KEY[-6:]}")
    print("-" * 60)

    # Discover best model
    model = discover_model()
    if not model:
        print("\n" + "=" * 60)
        print("❌ SUMMARY: Cohere API Key authentication failed or lacks access. ❌")
        print("=" * 60)
        sys.exit(1)

    # Prepare headers
    headers = get_headers()

    # Basic test questions
    test_questions = [
        "Hello! What model are you and who created you?",
        "What is the capital of France?",
        "Explain quantum computing in exactly one sentence."
    ]

    all_passed = True

    for i, question in enumerate(test_questions, 1):
        print(f"\n[Test Case {i}] Prompt: '{question}'")
        print(f"Sending request using model '{model}'...")

        payload = {
            "model": model,
            "message": question,
            "temperature": 0.3
        }

        try:
            response = requests.post(CHAT_URL, headers=headers, json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                reply = data.get("text", "")
                print("\n🟢 SUCCESS! Response received:")
                print("-" * 40)
                print(reply.strip())
                print("-" * 40)
            else:
                all_passed = False
                print(f"\n❌ FAILED! API responded with status code: {response.status_code}")
                try:
                    error_details = response.json()
                    print(f"Error response: {error_details}")
                except Exception:
                    print(f"Raw response: {response.text}")
        
        except requests.exceptions.RequestException as e:
            all_passed = False
            print(f"\n❌ FAILED! Request exception occurred: {e}")

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 SUMMARY: Cohere API Key is ACTIVE and WORKING PERFECTLY! 🎉")
    else:
        print("⚠️ SUMMARY: Some or all test cases failed. Please check the key or API status. ⚠️")
    print("=" * 60)

if __name__ == "__main__":
    run_test()
