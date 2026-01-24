"""Data models matching the frontend TypeScript interfaces."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class Creator(BaseModel):
    """Creator profile information."""
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    user_id: str


class Agent(BaseModel):
    """Agent profile information."""
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    base_url: Optional[str] = None  # Added field for base URL
    run_path: Optional[str] = None  # Added field for run path
    headers: Optional[Dict[str, str]] = None
    content_type: Optional[str] = None
    authentication: Optional[Dict[str, Any]] = None
    data_format: Optional[str] = None
    io_schema: Optional[Dict[str, Any]] = None
    out_schema: Optional[Dict[str, Any]] = None
    # data_structure: Optional[Dict[str, Any]] = None  # Changed to Dict
    
    tags: Optional[List[str]] = None
    model: Optional[str] = None
    status: Optional[str] = "draft"
    upvotes: Optional[int] = 0
    total_runs: Optional[int] = 0
    avg_rating: Optional[float] = 0
    success_rate: Optional[float] = 0
    avg_latency: Optional[int] = 0
    version: Optional[str] = "1.0.0"
    github_url: Optional[str] = None
    license: Optional[str] = "MIT"
    modalities: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    protocols: Optional[List[str]] = None
    dockerfile_url: Optional[str] = None
    runtime_dependencies: Optional[List[str]] = None
    creator_id: str
    created_at: datetime
    updated_at: datetime
    
    # data_structure: dict = {}  # Added field for data structure
    # NEW_SUPABASE_COLOUMN should be added here. 


class AgentWithCreator(Agent):
    """Agent with creator information."""
    creator: Creator


class SearchFilters(BaseModel):
    """Search and filter parameters."""
    search: str = ""
    category: str = ""
    model: str = ""
    modalities: List[str] = []
    capabilities: List[str] = []
    status: str = ""
    sort_by: str = "created_at"


class CreatorProfile(BaseModel):
    """Creator profile information."""
    id: str
    user_id: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    website_url: Optional[str] = None
    twitter_username: Optional[str] = None
    github_username: Optional[str] = None
    reputation_score: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

class Profile(BaseModel):
    """Creator profile information."""
    id: str
    username: str
    full_name: Optional[str] = None
    user_role: Optional[str] = None
    portfolio_url: Optional[str] = None
    expertise: Optional[str] = None
    primary_interest: Optional[str] = None
    github_url: Optional[str] = None
    email: Optional[str] = 0
    created_at: datetime
    memory: Optional[list[str]] = None #create a list of strings
    
class CreatorStats(BaseModel):
    """Creator statistics."""
    agent_count: int = 0
    total_runs: int = 0
    avg_rating: float = 0
    total_upvotes: int = 0


class CreatorWithStats(CreatorProfile):
    """Creator profile with statistics."""
    agent_count: int = 0
    total_runs: int = 0
    avg_rating: float = 0
    total_upvotes: int = 0