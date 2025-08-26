"""Creator services for managing creator profiles and leaderboards."""

from typing import List, Optional
from supabase_client import get_supabase_client
from models import CreatorProfile, CreatorWithStats


class CreatorService:
    """Service for managing creators."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def fetch_creators(self) -> List[CreatorWithStats]:
        """
        Fetch creators with their statistics.
        Mirrors the fetchCreators function from Creators.tsx.
        """
        try:
            # Fetch all creator profiles
            profiles_response = self.supabase.table('user_profiles').select('*').execute()
            
            if not profiles_response.data:
                return []
            
            creators_with_stats = []
            
            for profile in profiles_response.data:
                # Fetch agent statistics for this creator
                agents_response = self.supabase.table('agent_profiles').select(
                    'total_runs, avg_rating, upvotes'
                ).eq('creator_id', profile['user_id']).execute()
                
                # Calculate stats
                agent_count = len(agents_response.data) if agents_response.data else 0
                total_runs = sum(agent.get('total_runs', 0) for agent in agents_response.data) if agents_response.data else 0
                total_upvotes = sum(agent.get('upvotes', 0) for agent in agents_response.data) if agents_response.data else 0
                
                # Calculate average rating across all agents
                ratings = [agent.get('avg_rating', 0) for agent in agents_response.data if agent.get('avg_rating', 0) > 0] if agents_response.data else []
                avg_rating = sum(ratings) / len(ratings) if ratings else 0
                
                creator_with_stats = CreatorWithStats(
                    **profile,
                    agent_count=agent_count,
                    total_runs=total_runs,
                    avg_rating=avg_rating,
                    total_upvotes=total_upvotes
                )
                
                creators_with_stats.append(creator_with_stats)
            
            return creators_with_stats
            
        except Exception as e:
            print(f"Error fetching creators: {e}")
            raise e
    
    async def filter_and_sort_creators(
        self, 
        creators: List[CreatorWithStats], 
        search_term: str = "", 
        sort_by: str = "reputation"
    ) -> List[CreatorWithStats]:
        """
        Filter and sort creators.
        Mirrors the filterAndSortCreators function from Creators.tsx.
        """
        filtered_creators = creators
        
        # Apply search filter
        if search_term:
            search_lower = search_term.lower()
            filtered_creators = [
                creator for creator in creators
                if (creator.display_name and search_lower in creator.display_name.lower()) or
                   (creator.bio and search_lower in creator.bio.lower()) or
                   (creator.github_username and search_lower in creator.github_username.lower())
            ]
        
        # Apply sorting
        if sort_by == "reputation":
            filtered_creators.sort(key=lambda x: x.reputation_score or 0, reverse=True)
        elif sort_by == "agents":
            filtered_creators.sort(key=lambda x: x.agent_count, reverse=True)
        elif sort_by == "rating":
            filtered_creators.sort(key=lambda x: x.avg_rating, reverse=True)
        elif sort_by == "runs":
            filtered_creators.sort(key=lambda x: x.total_runs, reverse=True)
        elif sort_by == "name":
            filtered_creators.sort(key=lambda x: x.display_name or "")
        elif sort_by == "joined":
            filtered_creators.sort(key=lambda x: x.created_at, reverse=True)
        
        return filtered_creators
    
    async def get_leaderboard(self, limit: int = 50) -> List[CreatorWithStats]:
        """Get top creators for leaderboard."""
        try:
            creators = await self.fetch_creators()
            sorted_creators = await self.filter_and_sort_creators(creators, sort_by="reputation")
            return sorted_creators[:limit]
            
        except Exception as e:
            print(f"Error getting leaderboard: {e}")
            return []
    
    async def get_creator_by_id(self, user_id: str) -> Optional[CreatorWithStats]:
        """Get a single creator by user ID with statistics."""
        try:
            # Fetch creator profile
            profile_response = self.supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
            
            if not profile_response.data:
                return None
            
            profile = profile_response.data[0]
            
            # Fetch agent statistics
            agents_response = self.supabase.table('agent_profiles').select(
                'total_runs, avg_rating, upvotes'
            ).eq('creator_id', user_id).execute()
            
            # Calculate stats
            agent_count = len(agents_response.data) if agents_response.data else 0
            total_runs = sum(agent.get('total_runs', 0) for agent in agents_response.data) if agents_response.data else 0
            total_upvotes = sum(agent.get('upvotes', 0) for agent in agents_response.data) if agents_response.data else 0
            
            ratings = [agent.get('avg_rating', 0) for agent in agents_response.data if agent.get('avg_rating', 0) > 0] if agents_response.data else []
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            
            return CreatorWithStats(
                **profile,
                agent_count=agent_count,
                total_runs=total_runs,
                avg_rating=avg_rating,
                total_upvotes=total_upvotes
            )
            
        except Exception as e:
            print(f"Error fetching creator {user_id}: {e}")
            return None
    
    async def create_or_update_profile(self, user_id: str, profile_data: dict) -> Optional[CreatorProfile]:
        """Create or update a creator profile."""
        try:
            profile_data['user_id'] = user_id
            
            # Try to update first
            response = self.supabase.table('user_profiles').update(profile_data).eq('user_id', user_id).execute()
            
            # If no rows were updated, insert new profile
            if not response.data:
                response = self.supabase.table('user_profiles').insert(profile_data).execute()
            
            if response.data:
                return CreatorProfile(**response.data[0])
            return None
            
        except Exception as e:
            print(f"Error creating/updating profile: {e}")
            return None


# Initialize service instance
creator_service = CreatorService()