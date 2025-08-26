# AI Agent Marketplace - Python Backend

This Python backend mirrors the functionality of the React frontend, providing the same data fetching, filtering, and management capabilities using Supabase.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip or conda package manager

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials (already configured for this project)
   ```

3. **Run the FastAPI server:**
   ```bash
   python api/main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the API:**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - OpenAPI spec: http://localhost:8000/openapi.json

## 📁 Project Structure

```
backend_examples/python/
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── supabase_client.py       # Supabase client configuration
├── models.py                # Pydantic models (matches frontend types)
├── services/
│   ├── __init__.py
│   ├── agents.py           # Agent services (mirrors Explore.tsx)
│   └── creators.py         # Creator services (mirrors Creators.tsx)
├── api/
│   ├── __init__.py
│   └── main.py             # FastAPI endpoints
└── README.md               # This file
```

## 🔧 Usage Examples

### Using the Services Directly

```python
from services.agents import agent_service
from services.creators import creator_service
from models import SearchFilters

# Fetch agents with filters
filters = SearchFilters(
    search="chatbot",
    category="productivity",
    sort_by="popular"
)
agents = await agent_service.fetch_agents(filters)

# Get creator leaderboard
leaderboard = await creator_service.get_leaderboard(limit=10)
```

### Using the API Endpoints

```bash
# Get all agents
curl "http://localhost:8000/agents"

# Get agents with filters
curl "http://localhost:8000/agents?search=chatbot&category=productivity&sort_by=popular"

# Get creator leaderboard
curl "http://localhost:8000/creators/leaderboard?limit=10"

# Get specific agent
curl "http://localhost:8000/agents/{agent_id}"
```

## 🎯 Features

### Agent Management
- ✅ Fetch agents with search and filters
- ✅ Sort by popularity, rating, name, recent, created date
- ✅ Filter by category, model, status, modalities, capabilities
- ✅ Get agent details with creator information
- ✅ Create new agents
- ✅ Update agent status (verification)

### Creator Management
- ✅ Fetch creators with statistics
- ✅ Search and sort creators
- ✅ Get creator leaderboard
- ✅ Calculate creator stats (agent count, runs, ratings)
- ✅ Create/update creator profiles

### Data Models
- ✅ Pydantic models matching frontend TypeScript interfaces
- ✅ Type safety and validation
- ✅ Automatic JSON serialization

## 🔗 API Endpoints

### Agents
- `GET /agents` - Get agents with filters
- `GET /agents/{agent_id}` - Get specific agent
- `POST /agents` - Create new agent
- `PATCH /agents/{agent_id}/status` - Update agent status

### Creators
- `GET /creators` - Get creators with search/sort
- `GET /creators/leaderboard` - Get creator leaderboard
- `GET /creators/{user_id}` - Get specific creator
- `POST /creators/{user_id}/profile` - Create/update profile

## 🔄 Keeping in Sync with Frontend

This backend mirrors the frontend functionality:

- **`services/agents.py`** ↔ `pages/Explore.tsx`
- **`services/creators.py`** ↔ `pages/Creators.tsx`
- **`models.py`** ↔ TypeScript interfaces
- **`api/main.py`** ↔ API-like frontend queries

When the frontend changes, update the corresponding Python files to maintain feature parity.

## 🛠 Development

### Adding New Features

1. **Add new models** in `models.py`
2. **Implement business logic** in `services/`
3. **Add API endpoints** in `api/main.py`
4. **Update this README** with new endpoints

### Testing

```python
# Example test script
import asyncio
from services.agents import agent_service
from models import SearchFilters

async def test_agents():
    filters = SearchFilters(search="AI")
    agents = await agent_service.fetch_agents(filters)
    print(f"Found {len(agents)} agents")

if __name__ == "__main__":
    asyncio.run(test_agents())
```

## 📝 Notes

- This backend uses the same Supabase database as the frontend
- All RLS policies are respected through the Supabase client
- Authentication can be added by passing user tokens to the Supabase client
- The FastAPI server is optional - you can use the services directly in scripts

## 🤝 Contributing

When adding new features:
1. Update the corresponding service file
2. Add new API endpoints if needed
3. Update models if new data structures are required
4. Keep the README updated