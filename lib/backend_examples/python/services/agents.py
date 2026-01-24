"""Agent services for fetching and managing agents."""
import os
import sys
from typing import List, Optional, Tuple
from ..supabase_client import get_supabase_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Agent, AgentWithCreator, Creator, SearchFilters


class AgentService:
    """Service for managing agents."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def fetch_agents(self, filters: SearchFilters) -> List[AgentWithCreator]:
        """
        Fetch agents with filters and creator information.
        Mirrors the fetchAgents function from Explore.tsx.
        """
        try:
            # Start with base query
            query = self.supabase.table('agent_profiles').select('*')
            # print(f"query: {query}")
            # Apply filters
            if filters.search:
                # Search in name and description
                search_term = f"%{filters.search}%"
                query = query.or_(f"name.ilike.{search_term},description.ilike.{search_term}")
            
            if filters.category:
                query = query.eq('category', filters.category)
            
            # if filters.model:
            #     query = query.eq('model', filters.model)
            
            if filters.status:
                query = query.eq('status', filters.status)
            
            if filters.modalities:
                for modality in filters.modalities:
                    query = query.contains('modalities', [modality])
            
            if filters.capabilities:
                for capability in filters.capabilities:
                    query = query.contains('capabilities', [capability])
            
            # Apply sorting
            if filters.sort_by == 'popular':
                query = query.order('total_runs', desc=True)
            elif filters.sort_by == 'rating':
                query = query.order('avg_rating', desc=True)
            elif filters.sort_by == 'name':
                query = query.order('name')
            elif filters.sort_by == 'recent':
                query = query.order('updated_at', desc=True)
            else:  # created_at (default)
                query = query.order('created_at', desc=True)
            
            # Execute query
            response = query.execute()
            print(f"response: {response}")
            agents_data = response.data
            
            if not agents_data:
                return []
            
            # Fetch creator information for each agent
            creator_ids = list(set([agent['creator_id'] for agent in agents_data]))
            
            creators_response = self.supabase.table('user_profiles').select(
                'user_id, display_name, avatar_url'
            ).in_('user_id', creator_ids).execute()
            
            # Create creator lookup map
            creators_map = {
                creator['user_id']: Creator(
                    user_id=creator['user_id'],
                    display_name=creator['display_name'],
                    avatar_url=creator['avatar_url']
                )
                for creator in creators_response.data
            }
            
            # Combine agents with creator data
            agents_with_creators = []
            for agent_data in agents_data:
                agent = Agent(**agent_data)
                creator = creators_map.get(agent.creator_id)
                
                # Create AgentWithCreator
                agent_with_creator = AgentWithCreator(
                    **agent_data,
                    creator=creator if creator else Creator(
                        user_id=agent.creator_id,
                        display_name="Unknown Creator",
                        avatar_url=None
                    )
                )
                agents_with_creators.append(agent_with_creator)
            
            return agents_with_creators
            
        except Exception as e:
            print(f"Error fetching agents: {e}")
            raise e
    
    async def get_agent_by_id(self, agent_id: str) -> Optional[AgentWithCreator]:
        """Get a single agent by ID with creator information."""
        try:
            # Fetch agent
            agent_response = self.supabase.table('agent_profiles').select('*').eq('id', agent_id).execute()
            # print(f"agent_response: {agent_response}")
            # Includes base_url as a field in agent_response.
            if not agent_response.data:
                return None
            
            agent_data = agent_response.data[0]
            # print(f"agent_data: {agent_data}")
            # URL is present in agent_data if it exists.
            
            # Fetch creator
            creator_response = self.supabase.table('user_profiles').select(
                'user_id, display_name, avatar_url'
            ).eq('user_id', agent_data['creator_id']).execute()
            
            creator = None
            if creator_response.data:
                creator_data = creator_response.data[0]
                creator = Creator(
                    user_id=creator_data['user_id'],
                    display_name=creator_data['display_name'],
                    avatar_url=creator_data['avatar_url']
                )
            
            return AgentWithCreator(
                **agent_data,
                creator=creator if creator else Creator(
                    user_id=agent_data['creator_id'],
                    display_name="Unknown Creator",
                    avatar_url=None
                )
            )
            
        except Exception as e:
            print(f"Error fetching agent {agent_id}: {e}")
            return None
    
    async def create_agent(self, agent_data: dict, creator_id: str) -> Optional[Agent]:
        """Create a new agent."""
        try:
            agent_data['creator_id'] = creator_id
            response = self.supabase.table('agent_profiles').insert(agent_data).execute()
            
            if response.data:
                return Agent(**response.data[0])
            return None
            
        except Exception as e:
            print(f"Error creating agent: {e}")
            return None
    
    async def update_agent_status(self, agent_id: str, status: str) -> bool:
        """Update agent status (for verification)."""
        try:
            response = self.supabase.table('agent_profiles').update({
                'status': status
            }).eq('id', agent_id).execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            print(f"Error updating agent status: {e}")
            return False
    
    async def update_agent_field(self, agent_id: str, field: str, value):
        """Update a single field for an agent."""
        try:
            response = self.supabase.table('agent_profiles').update({
                field: value
            }).eq('id', agent_id).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating agent field: {e}")
            return False


# Initialize service instance
agent_service = AgentService()