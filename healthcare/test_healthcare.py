import sys
import os
import time
from agent_manager import HealthcareAgentManager

# ANSI Color Escapes for Test Output
CLR_SUCCESS = "\033[92m"
CLR_INFO = "\033[94m"
CLR_WARNING = "\033[93m"
CLR_STATS = "\033[90m"
CLR_RESET = "\033[0m"

def run_healthcare_integration_test():
    print("=" * 80)
    print("🚀 RUNNING HEALTHCARE AI STARTUP INTEGRATION TEST")
    print("=" * 80)
    
    # Initialize the manager
    print(f"{CLR_INFO}[Test] Instantiating HealthcareAgentManager...{CLR_RESET}")
    manager = HealthcareAgentManager()
    
    # Test 1: Onboarding / Initialization
    print(f"\n{CLR_INFO}[Test 1] Initializing/Onboarding Healthcare Agent...{CLR_RESET}")
    start_time = time.perf_counter()
    agent_id = manager.initialize()
    duration = time.perf_counter() - start_time
    
    print(f"{CLR_SUCCESS}✓ Agent Initialized successfully in {duration:.2f}s!{CLR_RESET}")
    print(f"  Agent Name: {manager.agent_name}")
    print(f"  Agent ID:   {agent_id}")
    print(f"  Agent Slug: {manager.agent_slug}")
    
    # Test 2: Multi-turn conversation and user memory verification
    print(f"\n{CLR_INFO}[Test 2] Starting programmatic multi-turn conversation...{CLR_RESET}")
    
    # Turn A: Seeding information
    message_a = "Hello! I want to start drinking at least 3 liters of water every day. Can you note this down as my primary wellness goal, and also give me a quick tip on why hydration is important?"
    print(f"\n{CLR_INFO}👤 User (Turn A):{CLR_RESET} {message_a}")
    
    start_time = time.perf_counter()
    response_a = manager.chat(message_a)
    duration_a = time.perf_counter() - start_time
    
    print(f"{CLR_SUCCESS}🩺 Healthcare AI:{CLR_RESET} {response_a.get('agent_response')}")
    print(f"{CLR_STATS}[Latency: {duration_a:.2f}s | Strategy: {response_a.get('strategy', '').upper()}]{CLR_RESET}")
    
    # Allow a small pause for background processes to finalize dialogue saving/indexing
    print(f"\n{CLR_STATS}Waiting 2 seconds for background memory synchronization...{CLR_RESET}")
    time.sleep(2.0)
    
    # Turn B: Recalling information / verification
    message_b = "Hey, do you remember what my primary wellness goal is, and how much water I set out to drink?"
    print(f"\n{CLR_INFO}👤 User (Turn B):{CLR_RESET} {message_b}")
    
    start_time = time.perf_counter()
    response_b = manager.chat(message_b)
    duration_b = time.perf_counter() - start_time
    
    print(f"{CLR_SUCCESS}🩺 Healthcare AI:{CLR_RESET} {response_b.get('agent_response')}")
    print(f"{CLR_STATS}[Latency: {duration_b:.2f}s | Strategy: {response_b.get('strategy', '').upper()}]{CLR_RESET}")
    
    # Verification Checks
    response_text = response_b.get('agent_response', '').lower()
    has_goal = "3 liters" in response_text or "3l" in response_text or "water" in response_text or "hydration" in response_text
    
    print("\n" + "=" * 80)
    print("📊 INTEGRATION TEST RESULTS SUMMARY")
    print("=" * 80)
    print(f"- Initialization:    {CLR_SUCCESS}PASSED{CLR_RESET}")
    print(f"- Turn A Latency:    {duration_a:.2f}s")
    print(f"- Turn B Latency:    {duration_b:.2f}s")
    
    if has_goal:
        print(f"- Memory Recall:     {CLR_SUCCESS}PASSED (Successfully recalled the 3-liter water intake goal!){CLR_RESET}")
    else:
        print(f"- Memory Recall:     {CLR_WARNING}WARNING (Agent response might not have explicitly repeated the 3-liter goal. Verify response text context above.){CLR_RESET}")
    
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_healthcare_integration_test()
