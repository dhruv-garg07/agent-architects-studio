#!/usr/bin/env python3
"""
Model Throughput Comparison Script
Compares the performance (TTFT, throughput, total latency) of:
1. OpenRouter model (nvidia/nemotron-3-nano-30b-a3b:free)
2. Claude model (e.g. claude-sonnet-4-6, claude-opus-4-7, claude-haiku-4-5-20251001)
"""

import os
import sys
import time
import json
import argparse
import requests
from dotenv import load_dotenv

# Try to load existing .env file
load_dotenv()

# ==============================================================================
# 🔑 BENCHMARK CONFIGURATION (Set your keys, models, and prompt here)
# ==============================================================================
# Put your API keys here. If left empty, the script automatically checks .env
OPENROUTER_API_KEY = "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"  # Place your OpenRouter key here
CLAUDE_API_KEY = "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"      # Place your Claude key here

# Models to benchmark
OPENROUTER_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"
CLAUDE_MODEL = "claude-sonnet-4-6"  # Active Claude model for this key (e.g. claude-sonnet-4-6, claude-opus-4-7)

# Test inputs
PROMPT = "Write a comprehensive explanation of quantum computing, its differences from classical computing, and its potential applications in cryptography and optimization. Aim for about 300 words."
MAX_TOKENS = 512
# ==============================================================================

# ANSI colors for beautiful terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def test_openrouter_throughput(api_key, model, prompt, max_tokens):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/dhruv-garg07/agent-architects-studio",
        "X-Title": "Agent Architects Studio Throughput Tool"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True
    }
    
    print(f"\n{Colors.BLUE}Starting OpenRouter stream ({model})...{Colors.ENDC}")
    
    start_time = time.time()
    ttft = None
    chunks_count = 0
    full_text = ""
    
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
        
        if response.status_code != 200:
            try:
                err_data = response.json()
                err_msg = err_data.get("error", {}).get("message", response.text)
                raise Exception(f"OpenRouter API Error ({response.status_code}): {err_msg}")
            except Exception:
                raise Exception(f"OpenRouter API Error ({response.status_code}): {response.text}")
                
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8').strip()
                if decoded_line.startswith('data: '):
                    data_str = decoded_line[6:]
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                if ttft is None:
                                    ttft = time.time() - start_time
                                    print(f"{Colors.GREEN}[OK] First token received in {ttft:.3f}s{Colors.ENDC}")
                                    print("Streaming response: ", end="", flush=True)
                                
                                chunks_count += 1
                                full_text += content
                                # Safe printing in Windows cmd/PowerShell to prevent encoding crashes
                                try:
                                    print(content, end="", flush=True)
                                except UnicodeEncodeError:
                                    print(content.encode('ascii', errors='replace').decode('ascii'), end="", flush=True)
                    except json.JSONDecodeError:
                        pass
                        
        print("\n")
        total_time = time.time() - start_time
        
        char_count = len(full_text)
        estimated_tokens = char_count / 4
        
        decode_time = total_time - ttft if ttft is not None else 0
        tps_decode = estimated_tokens / decode_time if decode_time > 0 else 0
        tps_overall = estimated_tokens / total_time if total_time > 0 else 0
        
        return {
            "success": True,
            "ttft": ttft,
            "total_time": total_time,
            "decode_time": decode_time,
            "char_count": char_count,
            "estimated_tokens": estimated_tokens,
            "tps_decode": tps_decode,
            "tps_overall": tps_overall
        }
        
    except Exception as e:
        print(f"\n{Colors.FAIL}OpenRouter throughput test failed: {e}{Colors.ENDC}")
        return {"success": False, "error": str(e)}

def test_claude_throughput(api_key, model, prompt, max_tokens):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True
    }
    
    print(f"\n{Colors.CYAN}Starting Anthropic Claude stream ({model})...{Colors.ENDC}")
    
    start_time = time.time()
    ttft = None
    chunks_count = 0
    full_text = ""
    
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
        
        if response.status_code != 200:
            try:
                err_data = response.json()
                err_msg = err_data.get("error", {}).get("message", response.text)
                raise Exception(f"Anthropic API Error ({response.status_code}): {err_msg}")
            except Exception:
                raise Exception(f"Anthropic API Error ({response.status_code}): {response.text}")
                
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8').strip()
                if decoded_line.startswith('data: '):
                    data_str = decoded_line[6:]
                    if not data_str.strip():
                        continue
                    
                    try:
                        data = json.loads(data_str)
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            content = delta.get("text", "")
                            if content:
                                if ttft is None:
                                    ttft = time.time() - start_time
                                    print(f"{Colors.GREEN}[OK] First token received in {ttft:.3f}s{Colors.ENDC}")
                                    print("Streaming response: ", end="", flush=True)
                                
                                chunks_count += 1
                                full_text += content
                                # Safe printing in Windows cmd/PowerShell to prevent encoding crashes
                                try:
                                    print(content, end="", flush=True)
                                except UnicodeEncodeError:
                                    print(content.encode('ascii', errors='replace').decode('ascii'), end="", flush=True)
                    except json.JSONDecodeError:
                        pass
                        
        print("\n")
        total_time = time.time() - start_time
        
        char_count = len(full_text)
        estimated_tokens = char_count / 4
        
        decode_time = total_time - ttft if ttft is not None else 0
        tps_decode = estimated_tokens / decode_time if decode_time > 0 else 0
        tps_overall = estimated_tokens / total_time if total_time > 0 else 0
        
        return {
            "success": True,
            "ttft": ttft,
            "total_time": total_time,
            "decode_time": decode_time,
            "char_count": char_count,
            "estimated_tokens": estimated_tokens,
            "tps_decode": tps_decode,
            "tps_overall": tps_overall
        }
        
    except Exception as e:
        print(f"\n{Colors.FAIL}Claude throughput test failed: {e}{Colors.ENDC}")
        return {"success": False, "error": str(e)}

def print_table(results_or, results_claude, or_model, claude_model):
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== Throughput Comparison Results ==={Colors.ENDC}")
    print(f"{'Metric':<30} | {'OpenRouter (Nemotron)':<25} | {'Claude (Anthropic)':<25}")
    print("-" * 88)
    
    model_name_or = or_model.split("/")[-1]
    model_name_claude = claude_model
    print(f"{'Model Name':<30} | {model_name_or:<25} | {model_name_claude:<25}")
    
    status_or = "Success" if results_or.get("success") else "Failed"
    status_claude = "Success" if results_claude.get("success") else "Failed"
    print(f"{'Status':<30} | {status_or:<25} | {status_claude:<25}")
    
    if results_or.get("success") and results_claude.get("success"):
        ttft_or = f"{results_or['ttft']:.3f} s"
        ttft_claude = f"{results_claude['ttft']:.3f} s"
        ttft_winner = "OpenRouter" if results_or['ttft'] < results_claude['ttft'] else "Claude"
        print(f"{'Time to First Token (TTFT)':<30} | {ttft_or:<25} | {ttft_claude:<25}")
        
        tot_or = f"{results_or['total_time']:.3f} s"
        tot_claude = f"{results_claude['total_time']:.3f} s"
        print(f"{'Total Latency':<30} | {tot_or:<25} | {tot_claude:<25}")
        
        gen_or = f"{results_or['decode_time']:.3f} s"
        gen_claude = f"{results_claude['decode_time']:.3f} s"
        print(f"{'Generation Time (after TTFT)':<30} | {gen_or:<25} | {gen_claude:<25}")
        
        char_or = f"{results_or['char_count']} chars"
        char_claude = f"{results_claude['char_count']} chars"
        print(f"{'Characters Generated':<30} | {char_or:<25} | {char_claude:<25}")
        
        tok_or = f"{results_or['estimated_tokens']:.1f} tokens"
        tok_claude = f"{results_claude['estimated_tokens']:.1f} tokens"
        print(f"{'Estimated Tokens (chars/4)':<30} | {tok_or:<25} | {tok_claude:<25}")
        
        tps_dec_or = f"{results_or['tps_decode']:.2f} t/s"
        tps_dec_claude = f"{results_claude['tps_decode']:.2f} t/s"
        tps_dec_winner = "OpenRouter" if results_or['tps_decode'] > results_claude['tps_decode'] else "Claude"
        print(f"{'Decoding Speed (after TTFT)':<30} | {tps_dec_or:<25} | {tps_dec_claude:<25}")
        
        tps_or = f"{results_or['tps_overall']:.2f} t/s"
        tps_claude = f"{results_claude['tps_overall']:.2f} t/s"
        print(f"{'Overall Speed (inc. TTFT)':<30} | {tps_or:<25} | {tps_claude:<25}")
        
        print("-" * 88)
        print(f"{Colors.BOLD}Key Takeaways:{Colors.ENDC}")
        print(f" • {Colors.BOLD}TTFT Winner:{Colors.ENDC} {Colors.GREEN if ttft_winner == 'OpenRouter' else Colors.CYAN}{ttft_winner}{Colors.ENDC}")
        print(f" • {Colors.BOLD}Decoding Speed Winner:{Colors.ENDC} {Colors.GREEN if tps_dec_winner == 'OpenRouter' else Colors.CYAN}{tps_dec_winner}{Colors.ENDC}")
    else:
        if not results_or.get("success"):
            print(f"{Colors.FAIL}OpenRouter Error: {results_or.get('error')}{Colors.ENDC}")
        if not results_claude.get("success"):
            print(f"{Colors.FAIL}Claude Error: {results_claude.get('error')}{Colors.ENDC}")

def clean_key(val, env_key):
    """Helper to check if a value is set and isn't a placeholder"""
    if val and not any(placeholder in val.lower() for placeholder in ["your-", "key-here", "placeholder"]):
        return val
    # Fallback to env
    return os.getenv(env_key) or ""

def main():
    # Load default configs from the top of the file
    or_key = clean_key(OPENROUTER_API_KEY, "OPENROUTER_API_KEY")
    claude_key = clean_key(CLAUDE_API_KEY, "CLAUDE_API_KEY")
    
    or_model = OPENROUTER_MODEL
    claude_model = CLAUDE_MODEL
    test_prompt = PROMPT
    max_tokens = MAX_TOKENS
    
    # CLI Overrides (if passed)
    parser = argparse.ArgumentParser(description="Compare throughput of OpenRouter and Anthropic Claude models.")
    parser.add_argument("--prompt", type=str, default=None, help="Override prompt.")
    parser.add_argument("--or-key", type=str, default=None, help="Override OpenRouter API Key.")
    parser.add_argument("--or-model", type=str, default=None, help="Override OpenRouter model.")
    parser.add_argument("--claude-key", type=str, default=None, help="Override Claude API Key.")
    parser.add_argument("--claude-model", type=str, default=None, help="Override Claude model.")
    parser.add_argument("--max-tokens", type=int, default=None, help="Override max tokens.")
    args = parser.parse_args()
    
    # Apply CLI overrides if provided
    if args.prompt is not None: test_prompt = args.prompt
    if args.or_key is not None: or_key = args.or_key
    if args.or_model is not None: or_model = args.or_model
    if args.claude_key is not None: claude_key = args.claude_key
    if args.claude_model is not None: claude_model = args.claude_model
    if args.max_tokens is not None: max_tokens = args.max_tokens

    print(f"{Colors.BOLD}{Colors.HEADER}================================================={Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}     LLM Throughput Benchmarking Tool           {Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}================================================={Colors.ENDC}")
    
    # Check keys
    api_error = False
    if not or_key:
        print(f"{Colors.WARNING}[WARNING] OpenRouter API key not configured.{Colors.ENDC}")
        api_error = True
    else:
        print(f"[OK] OpenRouter API Key loaded (ends in ...{or_key[-6:] if len(or_key) > 6 else or_key})")
        
    if not claude_key:
        print(f"{Colors.WARNING}[WARNING] Claude API key (CLAUDE_API_KEY) not configured.{Colors.ENDC}")
        api_error = True
    else:
        print(f"[OK] Claude API Key loaded (ends in ...{claude_key[-6:] if len(claude_key) > 6 else claude_key})")
        
    if api_error:
        print(f"\n{Colors.WARNING}Please enter keys to continue (or press Enter to skip a test):{Colors.ENDC}")
        if not or_key:
            or_key = input("Enter OpenRouter API Key: ").strip()
        if not claude_key:
            claude_key = input("Enter Claude API Key: ").strip()

    if not or_key and not claude_key:
        print(f"{Colors.FAIL}Error: No API keys provided. Exiting.{Colors.ENDC}")
        sys.exit(1)
        
    print(f"\nPrompt: \"{Colors.BOLD}{test_prompt}{Colors.ENDC}\"")
    print(f"Max tokens to generate: {max_tokens}")
    
    results_or = {"success": False, "error": "Test not run (missing key)"}
    results_claude = {"success": False, "error": "Test not run (missing key)"}
    
    if or_key:
        results_or = test_openrouter_throughput(or_key, or_model, test_prompt, max_tokens)
        
    if claude_key:
        results_claude = test_claude_throughput(claude_key, claude_model, test_prompt, max_tokens)
        
    print_table(results_or, results_claude, or_model, claude_model)

if __name__ == "__main__":
    main()
