# AI Agent Marketplace - Flask Application

A complete Python Flask web application for the AI Agent Marketplace, converted from the original React/TypeScript frontend.

## Features

- **Homepage**: Hero section with featured agents and categories
- **Explore**: Browse and filter AI agents with advanced search
- **Agent Details**: Comprehensive agent information and deployment options
- **Creators**: Community directory with creator profiles and statistics
- **Creator Studio**: Submit new agents for review
- **Authentication**: User login/registration system
- **Responsive Design**: Mobile-friendly interface with Tailwind CSS

## Quick Start

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ai-agent-marketplace
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Open your browser**:
   Navigate to `http://localhost:5000`

## Project Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/            # Jinja2 HTML templates
│   ├── base.html         # Base template with navigation
│   ├── homepage.html     # Landing page
│   ├── explore.html      # Agent browser
│   ├── agent_detail.html # Individual agent page
│   ├── creators.html     # Creator directory
│   ├── creator_studio.html # Agent submission form
│   ├── auth.html         # Login/register page
│   ├── 404.html          # Not found page
│   └── 500.html          # Error page
├── backend_examples/     # Python backend services
│   └── python/           # Supabase integration
│       ├── services/     # Business logic
│       └── models.py     # Data models
└── static/               # Static assets (optional)
```

## Core Features

### 1. Agent Exploration
- Advanced search and filtering
- Category-based browsing
- Sort by popularity, rating, date
- Filter by model, capabilities, modalities

### 2. Agent Details
- Comprehensive agent information
- Technical specifications
- Creator profiles
- Performance metrics
- Deployment options

### 3. Creator Community
- Creator profiles with statistics
- Social links and portfolios
- Agent portfolios
- Reputation system

### 4. Agent Submission
- Step-by-step submission form
- Technical specifications
- Repository integration
- Review process

### 5. Authentication
- Email/password registration
- Social login support (GitHub, Google)
- Session management
- Protected routes

## Backend Integration

The application uses the Python services from `backend_examples/python/` for:

- **Agent Service**: Fetch, filter, and manage agents
- **Creator Service**: Handle creator profiles and statistics
- **Supabase Integration**: Database operations and authentication

### Key Services

```python
from backend_examples.python.services.agents import agent_service
from backend_examples.python.services.creators import creator_service

# Fetch agents with filters
agents = agent_service.fetch_agents(filters)

# Get creator statistics
creators = creator_service.fetch_creators()
```

## Database Schema

The application expects these Supabase tables:

- `agent_profiles`: Agent information and metadata
- `user_profiles`: Creator profiles and statistics
- Authentication handled by Supabase Auth

## Customization

### Styling
The application uses a custom design system with:
- Tailwind CSS for utility classes
- CSS custom properties for theming
- Responsive design patterns
- Dark/light mode support

### Adding Features
1. Create new routes in `app.py`
2. Add corresponding templates in `templates/`
3. Extend services in `backend_examples/python/`
4. Update navigation in `base.html`

## Environment Variables

Required environment variables in `.env`:

```env
SECRET_KEY=your-secret-key-here
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
```

## Deployment

### Local Development
```bash
python app.py
```

### Production Deployment
1. **Using Gunicorn**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Using Docker**:
   ```dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 5000
   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
   ```

3. **Deploy to platforms**:
   - Heroku
   - Railway
   - DigitalOcean App Platform
   - AWS Elastic Beanstalk

## API Endpoints

The application provides both web routes and API endpoints:

### Web Routes
- `GET /` - Homepage
- `GET /explore` - Agent browser
- `GET /agent/<id>` - Agent details
- `GET /creators` - Creator directory
- `GET /submit` - Agent submission form
- `GET /auth` - Authentication page

### API Routes
- `GET /api/agents` - Fetch agents (JSON)
- `GET /api/creators` - Fetch creators (JSON)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.