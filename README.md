# Food AI Agent

AI-powered food service management platform for Korean institutional food service operations. Built with FastAPI + Next.js, featuring AI-driven menu planning, HACCP compliance management, and recipe operations.

## Architecture

```
food-ai-agent-api/      # FastAPI backend (Python 3.11)
food-ai-agent-web/      # Next.js 14 frontend (TypeScript)
docker-compose.yml      # Production-like environment
docker-compose.dev.yml  # Development overrides (hot reload)
Makefile                # Convenience commands
```

### Backend Stack
- **FastAPI** 0.110+ with async SQLAlchemy 2.0 (asyncpg)
- **PostgreSQL 16** with pgvector extension for vector embeddings
- **Alembic** for async database migrations
- **JWT** authentication (python-jose + passlib/bcrypt)
- **Anthropic Claude** for AI menu generation and chat
- **OpenAI** for text embeddings (RAG pipeline)

### Frontend Stack
- **Next.js 14** App Router + TypeScript (strict)
- **Tailwind CSS 3** + shadcn/ui component system
- **Zustand 4** for client state
- **TanStack Query 5** for server state management
- **SSE** streaming for AI chat responses

## Quick Start with Docker Compose

### Prerequisites
- Docker and Docker Compose
- (Optional) Anthropic API key for AI features
- (Optional) OpenAI API key for embeddings

### 1. Environment Setup

```bash
# Optional: set API keys for AI features
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
```

### 2. Start All Services

```bash
# Production-like mode
docker compose up --build

# Development mode with hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Or using Make
make up    # production-like
make dev   # development with hot reload
```

This starts:
- **PostgreSQL** (pgvector) on port 5432
- **Backend API** on port 8000 (auto-runs migrations + seed data)
- **Frontend** on port 3000

### 3. Access the Application

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/api/v1/docs
- Health Check: http://localhost:8000/health

### Seed Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@smallsf.com | admin1234 |
| Nutritionist | nutritionist@smallsf.com | nut1234 |
| Kitchen | kitchen@smallsf.com | kit1234 |
| Quality | quality@smallsf.com | qlt1234 |

## Local Development (without Docker)

### Backend

```bash
cd food-ai-agent-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Edit with your database URL and API keys

# Run migrations
alembic -c alembic/alembic.ini upgrade head

# Seed data
python -m app.seed

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd food-ai-agent-web

# Install dependencies
npm install

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local

# Start dev server
npm run dev
```

## Environment Variables

### Backend (`food-ai-agent-api/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@localhost:5432/food_ai_agent` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT signing secret |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins (JSON array) |
| `ANTHROPIC_API_KEY` | (empty) | Anthropic API key for Claude |
| `OPENAI_API_KEY` | (empty) | OpenAI API key for embeddings |
| `APP_ENV` | `development` | Application environment |
| `DEBUG` | `true` | Enable debug mode |

### Frontend (`food-ai-agent-web/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Backend API base URL |

## User Roles (RBAC)

| Code | Role | Permissions |
|------|------|-------------|
| `ADM` | Administrator | Full access, user management, confirm menu plans |
| `NUT` | Nutritionist | Menu planning, recipe management, policy setup |
| `KIT` | Kitchen Staff | Work orders, recipe scaling, CCP records |
| `QLT` | Quality Manager | HACCP checklists, incidents, audit reports |
| `OPS` | Operations | Menu confirmation, dashboard, cross-site oversight |

## API Endpoints

| Module | Prefix | Description |
|--------|--------|-------------|
| Auth | `/api/v1/auth` | Login, register, refresh, me |
| Menu Plans | `/api/v1/menu-plans` | CRUD, generate, validate, confirm |
| Recipes | `/api/v1/recipes` | CRUD, search, scale |
| Work Orders | `/api/v1/work-orders` | Generate, list, status updates |
| HACCP | `/api/v1/haccp` | Checklists, CCP records, incidents, reports |
| Dashboard | `/api/v1/dashboard` | Overview stats, alerts |
| Chat | `/api/v1/chat` | AI chat with SSE streaming |
| Sites | `/api/v1/sites` | Site management |
| Items | `/api/v1/items` | Food item catalog |
| Policies | `/api/v1/policies` | Nutrition & allergen policies |

## Testing

```bash
cd food-ai-agent-api

# Install dev dependencies
pip install -r requirements-dev.txt

# Requires a test PostgreSQL database: food_ai_agent_test
# The test config auto-derives from DATABASE_URL by replacing the DB name

# Run all tests
pytest

# Run specific test module
pytest tests/test_auth.py
pytest tests/test_menu_plans.py
pytest tests/test_haccp.py
pytest tests/test_chat.py

# Run with verbose output
pytest -v

# Via Docker
make test
```

### Test Coverage
- **Auth** (9 tests): login, register, refresh, /me, error cases
- **Menu Plans** (10 tests): generate, list, detail, validate, confirm, update, RBAC
- **HACCP** (14 tests): checklists, CCP records, incidents, audit reports
- **Chat** (5 tests): SSE streaming with mock Anthropic, conversations, auth

## Database Schema

14 tables including:
- `sites`, `users` - Multi-site and user management
- `items` - Food item catalog with allergen tracking
- `nutrition_policies`, `allergen_policies` - Site-level compliance rules
- `recipes` - Recipe library with ingredients, steps, CCP points
- `recipe_documents` - RAG document store with pgvector embeddings (1536d)
- `menu_plans`, `menu_plan_items`, `menu_plan_validations` - Menu planning workflow
- `work_orders` - Kitchen production orders with scaled ingredients
- `haccp_checklists`, `haccp_records`, `haccp_incidents` - HACCP compliance
- `audit_logs` - Full audit trail
- `conversations` - AI chat history

## Key Features

- **AI Menu Generation**: Generate weekly menu plans considering nutrition policies, allergens, budget, and diversity
- **Nutrition Validation**: Automated daily nutrition checks against site policies (kcal, protein, sodium)
- **Recipe Scaling**: Scale recipes to target servings with seasoning adjustment factors for large batches
- **HACCP Management**: Daily/weekly checklists, CCP temperature recording, incident reporting with severity-based response steps
- **22 Korean Allergens**: Full tracking of legally required allergens
- **Audit Trail**: Complete audit logging for all operations
- **Real-time Chat**: AI assistant with SSE streaming, context-aware of current page

## Make Commands

| Command | Description |
|---------|-------------|
| `make up` | Start all services (detached) |
| `make down` | Stop all services |
| `make dev` | Start with hot reload (development) |
| `make seed` | Run seed data |
| `make test` | Run backend tests |
| `make migrate` | Run database migrations |
| `make logs` | Tail service logs |
| `make clean` | Stop services and remove volumes |
