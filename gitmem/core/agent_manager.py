from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from .models import AgentProfile

class AgentManager:
    def __init__(self, memory_store):
        self.store = memory_store
        # In-memory registry for specialized runtime stats (heartbeats)
        # In production this would be Redis
        self._active_agents: Dict[str, Dict[str, Any]] = {}
        
    def register_heartbeat(self, agent_id: str, model: str = None):
        """Update the last_seen timestamp for an agent."""
        self._active_agents[agent_id] = {
            "last_seen": datetime.now(),
            "model": model or "GPT-4"
        }
        
    def get_online_agents(self, timeout_seconds=300) -> List[str]:
        """Get list of agents active within timeout window."""
        now = datetime.now()
        threshold = now - timedelta(seconds=timeout_seconds)
        
        # Purge old
        active = []
        for aid, data in list(self._active_agents.items()):
            if data["last_seen"] > threshold:
                active.append(aid)
            else:
                del self._active_agents[aid]
        return active
    
    def get_agent_count(self) -> int:
        return len(self.get_online_agents())
    
    def get_active_agents(self, timeout_seconds=300) -> List[Dict[str, Any]]:
        """Get detailed list of currently active agents."""
        now = datetime.now()
        threshold = now - timedelta(seconds=timeout_seconds)
        
        agents = []
        for aid, data in list(self._active_agents.items()):
            last_seen = data["last_seen"]
            if last_seen > threshold:
                # Calculate relative time
                delta = now - last_seen
                if delta.seconds < 60:
                    relative_time = f"{delta.seconds}s ago"
                elif delta.seconds < 3600:
                    relative_time = f"{delta.seconds // 60}m ago"
                else:
                    relative_time = f"{delta.seconds // 3600}h ago"
                
                agents.append({
                    "agent_id": aid,
                    "model": data.get("model", "GPT-4"),
                    "status": "online",
                    "last_active": relative_time,
                    "last_seen_iso": last_seen.isoformat()
                })
            else:
                del self._active_agents[aid]
        
        return agents
    
    def get_profile(self, agent_id: str) -> Optional[AgentProfile]:
        # TODO: Load from persistent storage in MemoryStore
        # For now, return a mock profile if online, else None
        if agent_id in self._active_agents:
            return AgentProfile(
                id=agent_id,
                name=f"Agent-{agent_id}",
                description="Autonomous Agent",
                last_seen=self._active_agents[agent_id]["last_seen"],
                status="online"
            )
        return None
