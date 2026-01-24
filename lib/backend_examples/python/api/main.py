"""FastAPI application with endpoints mirroring frontend functionality."""
import os
import sys
from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import AgentWithCreator, CreatorWithStats, SearchFilters
from services.agents import agent_service
from services.creators import creator_service



app = FastAPI(title="AI Agent Marketplace API", version="1.0.0")

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI Agent Marketplace API"}

# Agent endpoints
@app.get("/agents", response_model=List[AgentWithCreator])
async def get_agents(
    search: str = Query("", description="Search term"),
    category: str = Query("", description="Filter by category"),
    model: str = Query("", description="Filter by model"),
    status: str = Query("", description="Filter by status"),
    sort_by: str = Query("created_at", description="Sort by field"),
    modalities: List[str] = Query([], description="Filter by modalities"),
    capabilities: List[str] = Query([], description="Filter by capabilities")
):
    """Get agents with filters and creator information."""
    try:
        filters = SearchFilters(
            search=search,
            category=category,
            model=model,
            status=status,
            sort_by=sort_by,
            modalities=modalities,
            capabilities=capabilities
        )
        agents = await agent_service.fetch_agents(filters)
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/{agent_id}", response_model=AgentWithCreator)
async def get_agent(agent_id: str):
    """Get a single agent by ID."""
    try:
        agent = await agent_service.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents", response_model=AgentWithCreator)
async def create_agent(agent_data: dict, creator_id: str):
    """Create a new agent."""
    try:
        agent = await agent_service.create_agent(agent_data, creator_id)
        if not agent:
            raise HTTPException(status_code=400, detail="Failed to create agent")
        
        # Return agent with creator info
        agent_with_creator = await agent_service.get_agent_by_id(agent.id)
        return agent_with_creator
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/agents/{agent_id}/status")
async def update_agent_status(agent_id: str, status: str):
    """Update agent status (for verification)."""
    try:
        success = await agent_service.update_agent_status(agent_id, status)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update agent status")
        return {"message": "Agent status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Creator endpoints
@app.get("/creators", response_model=List[CreatorWithStats])
async def get_creators(
    search: str = Query("", description="Search term"),
    sort_by: str = Query("reputation", description="Sort by field")
):
    """Get creators with statistics."""
    try:
        creators = await creator_service.fetch_creators()
        filtered_creators = await creator_service.filter_and_sort_creators(creators, search, sort_by)
        return filtered_creators
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/creators/leaderboard", response_model=List[CreatorWithStats])
async def get_leaderboard(limit: int = Query(50, description="Number of creators to return")):
    """Get creator leaderboard."""
    try:
        leaderboard = await creator_service.get_leaderboard(limit)
        return leaderboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/creators/{user_id}", response_model=CreatorWithStats)
async def get_creator(user_id: str):
    """Get a single creator by user ID."""
    try:
        creator = await creator_service.get_creator_by_id(user_id)
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found")
        return creator
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/creators/{user_id}/profile")
async def create_or_update_profile(user_id: str, profile_data: dict):
    """Create or update creator profile."""
    try:
        profile = await creator_service.create_or_update_profile(user_id, profile_data)
        if not profile:
            raise HTTPException(status_code=400, detail="Failed to create/update profile")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)