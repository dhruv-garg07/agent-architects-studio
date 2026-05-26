import sys
import os
import time
from agent_manager import HealthcareAgentManager

# ANSI Color Escapes for Premium Terminal Aesthetics
CLR_HEADER = "\033[95m"
CLR_TITLE = "\033[1;36m"
CLR_USER = "\033[94m"
CLR_AI = "\033[92m"
CLR_WARNING = "\033[93m"
CLR_STATS = "\033[90m"
CLR_RESET = "\033[0m"

def display_banner():
    banner = f"""{CLR_TITLE}
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║     🩺   H E A L T H C A R E   A I   S T A R T U P   P O R T A L   🩺    ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝{CLR_RESET}"""
    print(banner)

def run_chatbox():
    display_banner()
    
    print(f"{CLR_STATS}Connecting to Manhattan Agent Platform...{CLR_RESET}")
    try:
        manager = HealthcareAgentManager()
        agent_id = manager.initialize()
        
        # Display session details in a beautiful box
        print(f"\n{CLR_HEADER}┌───────────────────────── ACTIVE SESSION ─────────────────────────┐{CLR_RESET}")
        print(f"{CLR_HEADER}│{CLR_RESET}  {CLR_TITLE}Agent Name:{CLR_RESET}  {manager.agent_name:<47} {CLR_HEADER}│{CLR_RESET}")
        print(f"{CLR_HEADER}│{CLR_RESET}  {CLR_TITLE}Agent Slug:{CLR_RESET}  {manager.agent_slug:<47} {CLR_HEADER}│{CLR_RESET}")
        print(f"{CLR_HEADER}│{CLR_RESET}  {CLR_TITLE}Agent ID  :{CLR_RESET}  {agent_id:<47} {CLR_HEADER}│{CLR_RESET}")
        print(f"{CLR_HEADER}│{CLR_RESET}  {CLR_TITLE}Platform  :{CLR_RESET}  {manager.base_url:<47} {CLR_HEADER}│{CLR_RESET}")
        print(f"{CLR_HEADER}└──────────────────────────────────────────────────────────────────┘{CLR_RESET}\n")
        
        print(f"{CLR_WARNING}⚠️  Medical Disclaimer: This AI is a lifestyle coach and does not provide clinical advice.{CLR_RESET}\n")
        print(f"Type '{CLR_TITLE}exit{CLR_RESET}' or '{CLR_TITLE}quit{CLR_RESET}' to end the conversation.\n")
        
        # Prime conversation with an introductory message
        print(f"{CLR_AI}🩺 Healthcare AI:{CLR_RESET} Hello! I am your Healthcare AI Assistant. How can I assist you with your health logs, hydration tracking, or wellness goals today?\n")
        
        while True:
            try:
                user_input = input(f"{CLR_USER}👤 You:{CLR_RESET} ")
                if not user_input.strip():
                    continue
                
                if user_input.strip().lower() in ["exit", "quit"]:
                    print(f"\n{CLR_TITLE}Thank you for using Healthcare AI Startup. Stay healthy!{CLR_RESET}")
                    break
                
                print(f"{CLR_STATS}Thinking...{CLR_RESET}", end="\r")
                
                start_time = time.perf_counter()
                response_data = manager.chat(user_input)
                duration = time.perf_counter() - start_time
                
                # Clear "Thinking..." line
                print(" " * 20, end="\r")
                
                ai_response = response_data.get("agent_response", "Error: No response generated.")
                strategy = response_data.get("strategy", "unknown")
                
                # Display AI response
                print(f"{CLR_AI}🩺 Healthcare AI:{CLR_RESET} {ai_response}\n")
                
                # Display latency & routing statistics
                print(f"{CLR_STATS}[Latency: {duration:.2f}s | Strategy: {strategy.upper()}]{CLR_RESET}\n")
                
            except KeyboardInterrupt:
                print(f"\n\n{CLR_TITLE}Session interrupted. Stay healthy!{CLR_RESET}")
                break
            except Exception as e:
                print(f"{CLR_WARNING}Error sending message: {e}{CLR_RESET}\n")
                
    except Exception as e:
        print(f"{CLR_WARNING}Failed to initialize chatbox: {e}{CLR_RESET}")
        sys.exit(1)

if __name__ == "__main__":
    run_chatbox()
