import os
import json
import requests
from typing import Dict, Any, Optional

class HealthcareAgentManager:
    """
    Manager for the Healthcare AI Startup Agent.
    Handles agent discovery, initialization, creation, and chat interactions.
    """
    def __init__(
        self, 
        api_key: str = "sk-NRT-HUMD_Q5MqSsP60xh3gwx-gQuD82KBivp2NfrQUg",
        base_url: str = "https://www.themanhattanproject.ai",
        config_path: str = None
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        
        # Setup config path
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_path = os.path.join(current_dir, "agent_config.json")
        else:
            self.config_path = config_path
            
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.agent_id = "b431c5f5-2556-4768-9959-838eeefbb952"
        self.agent_slug = "healthcare-ai-assistant-dhruv"
        self.agent_name = "Healthcare AI Assistant"
        self.system_prompt = (
            "You are an advanced healthcare companion and lifestyle coach AI developed by a premium healthcare startup. "
            "Your goal is to help users track healthy habits (like water intake, sleep, exercise) and discuss wellness goals. "
            "IMPORTANT: You are an AI assistant, not a medical professional. Always maintain a warm, supportive, yet "
            "professional tone. If the user reports severe symptoms (e.g. chest pain, breathing difficulty, extreme sudden pain), "
            "kindly but firmly urge them to seek emergency medical care immediately. For general health logs, offer evidence-based "
            "lifestyle, nutrition, hydration, and exercise suggestions while reminding them to consult a certified physician "
            "for medical diagnoses."
        )

    def initialize(self) -> str:
        """
        Ensures that the healthcare agent exists.
        First checks local config, then lists remote agents, and creates one if not found.
        """
        # 1. Check local config first
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                    if config.get("agent_id") and config.get("agent_slug") == self.agent_slug:
                        self.agent_id = config["agent_id"]
                        print(f"[Init] Loaded existing agent ID from local config: {self.agent_id}")
                        # Verify agent exists remotely
                        if self._verify_agent_remotely(self.agent_id):
                            return self.agent_id
                        else:
                            print("[Init] Local agent ID not valid remotely. Proceeding to search/recreate.")
            except Exception as e:
                print(f"[Init] Error reading local config: {e}")

        # 2. Check remote agents to prevent duplicate slugs
        print("[Init] Searching remote agents for matching slug...")
        remote_agent_id = self._find_agent_by_slug(self.agent_slug)
        if remote_agent_id:
            self.agent_id = remote_agent_id
            self._save_config()
            print(f"[Init] Found existing agent remotely: {self.agent_id}")
            return self.agent_id

        # 3. Create a new agent if not found
        print("[Init] Agent not found. Creating a new healthcare agent...")
        new_agent_id = self._create_agent_remotely()
        if new_agent_id:
            self.agent_id = new_agent_id
            self._save_config()
            print(f"[Init] Successfully created and configured healthcare agent: {self.agent_id}")
            return self.agent_id
        else:
            raise RuntimeError("Failed to initialize healthcare agent.")

    def _verify_agent_remotely(self, agent_id: str) -> bool:
        """Verify that the agent ID is valid and exists on the remote server."""
        url = f"{self.base_url}/get_agent"
        params = {"agent_id": agent_id}
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            return response.status_code == 200
        except Exception as e:
            print(f"[Verify] Request failed: {e}")
            return False

    def _find_agent_by_slug(self, slug: str) -> Optional[str]:
        """Search remote agents by slug and return its agent_id if found."""
        url = f"{self.base_url}/list_agents"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                agents = response.json()
                if isinstance(agents, list):
                    for agent in agents:
                        if agent.get("agent_slug") == slug:
                            return agent.get("agent_id")
            else:
                print(f"[Search] List agents failed with status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[Search] Request failed: {e}")
        return None

    def _create_agent_remotely(self) -> Optional[str]:
        """Create the agent via POST /create_agent."""
        url = f"{self.base_url}/create_agent"
        payload = {
            "agent_name": self.agent_name,
            "agent_slug": self.agent_slug,
            "system_prompt": self.system_prompt,
            "permissions": {"chat": True, "embeddings": True},
            "limits": {"rpm": 20},
            "metadata": {"startup": "healthcare-ai-startup"}
        }
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=20)
            if response.status_code in (200, 201):
                res_json = response.json()
                return res_json.get("agent_id")
            else:
                print(f"[Create] Failed to create agent: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[Create] Request failed: {e}")
        return None

    def _save_config(self):
        """Save current agent configuration locally."""
        try:
            with open(self.config_path, "w") as f:
                json.dump({
                    "agent_id": self.agent_id,
                    "agent_slug": self.agent_slug,
                    "agent_name": self.agent_name
                }, f, indent=4)
        except Exception as e:
            print(f"[Config] Failed to save local config: {e}")

    def chat(self, message: str, strategy: str = "auto") -> Dict[str, Any]:
        """
        Send a message to the healthcare agent via /agent_chat.
        Returns the API response JSON.
        """
        if not self.agent_id:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        url = f"{self.base_url}/agent_chat"
        payload = {
            "agent_id": self.agent_id,
            "message": message,
            "strategy": strategy
        }
        
        response = requests.post(url, headers=self.headers, json=payload, timeout=120)
        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(f"Chat API error (Status {response.status_code}): {response.text}")
