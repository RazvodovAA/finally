# FinAlly Agent Team

## Team Composition

This project is built by a coordinated team of specialized agents:

1. **Database Engineer** (Task #2)
   - Schema design, SQLite initialization, seed data
   - Deliverable: working DB module at `backend/app/db/`
   - No dependencies — starts first

2. **Market Data Engineer** (Task #3)
   - Simulator, Massive API, price cache, SSE streaming
   - Depends on: Database (Task #2)
   - Deliverable: market data subsystem at `backend/app/market/`

3. **Backend API Engineer** (Task #4)
   - FastAPI endpoints (portfolio, watchlist, trades, health)
   - Depends on: Database (Task #2), Market Data (Task #3)
   - Deliverable: working REST API at `backend/app/routes/`

4. **LLM Engineer** (Task #5)
   - OpenAI/LiteLLM integration, structured outputs, chat endpoint
   - Depends on: Backend API (Task #4)
   - Deliverable: LLM subsystem at `backend/app/llm/`

5. **Frontend Engineer** (Task #6)
   - React/TypeScript UI, SSE client, charts, trading interface
   - Depends on: Backend API (Task #4)
   - Deliverable: Next.js SPA at `frontend/`

6. **Integration Tester** (Task #7)
   - E2E Playwright tests, bug triage and reporting
   - Depends on: Backend API, LLM, Frontend, DevOps (Tasks #4, #5, #6, #8)
   - Deliverable: passing test suite at `test/`

7. **DevOps Engineer** (Task #8)
   - Docker multi-stage build, docker-compose, start/stop scripts
   - Depends on: Backend API, LLM, Frontend (Tasks #4, #5, #6)
   - Deliverable: Dockerfile, scripts, docker-compose files

## Execution Order

1. **Phase 1 — Foundation** (in parallel):
   - Database Engineer: implement schema and lazy initialization
   - DevOps Engineer: begin Docker setup with basic structure

2. **Phase 2 — Data Layer** (in parallel):
   - Market Data Engineer: implement simulator + Massive API (unblocked by Phase 1)
   - Backend API Engineer: implement endpoints (unblocked by Phases 1+2)

3. **Phase 3 — Application** (in parallel):
   - LLM Engineer: implement chat (unblocked by Phase 2)
   - Frontend Engineer: build UI components (unblocked by Phase 2)
   - DevOps Engineer: finalize Docker image and scripts (unblocked by Phase 2)

4. **Phase 4 — Testing & Polish**:
   - Integration Tester: run E2E tests, file bugs
   - Each team member: fix assigned bugs
   - Team: iterate until all tests pass

## Communication

- **Planning directory** (`planning/`): shared source of truth
  - PLAN.md: project specification (frozen)
  - TEAM.md: this file (team structure and coordination)
  - Team updates and notes as needed
- **Code**: Each module imports from well-defined interfaces
  - Market Data module exports: `PriceCache`, `PriceUpdate`, `MarketDataSource`, `create_market_data_source`, `create_stream_router`
  - Backend API routes import from market data, DB, LLM modules
  - Frontend imports from `/api/*` endpoints (no cross-module imports)
- **Bug Reports**: Integration Tester files issues in code comments or planning directory, tags responsible engineer
- **Git commits**: Each agent commits their work with clear messages

## Key Interfaces

### Market Data (`app/market/__init__.py`)

```python
from app.market import (
    PriceCache,
    PriceUpdate,
    MarketDataSource,
    create_market_data_source,
    create_stream_router
)
```

### Database (`app/db/__init__.py`)

```python
from app.db import (
    init_db,
    get_db_connection,
    execute_query,
    execute_insert,
    # Table-specific functions
)
```

### LLM (`app/llm/__init__.py`)

```python
from app.llm import (
    process_chat_message,
    ChatResponse,
    execute_trades,
    execute_watchlist_changes
)
```

## Testing Strategy

- **Unit tests**: Each engineer writes tests for their module
- **Integration tests**: Backend API Engineer writes tests for endpoint+DB+market data interactions
- **E2E tests**: Integration Tester writes browser-level tests covering full user journeys
- **Mock mode**: LLM Engineer provides deterministic mock responses for reproducible tests

## Deployment Checklist

Before final testing:
- [ ] Docker image builds without errors
- [ ] Container starts and health check passes
- [ ] All API endpoints respond
- [ ] SSE streaming works
- [ ] Chat endpoint processes messages
- [ ] Frontend loads and renders
- [ ] Start/stop scripts are idempotent

## Next Steps

1. Database Engineer starts Task #2
2. DevOps Engineer begins Docker skeleton (Task #8)
3. Upon Database completion, Market Data Engineer starts Task #3
4. Upon Database+Market Data completion, Backend API and Frontend engineers start Tasks #4 and #6
5. Upon Backend API completion, LLM Engineer starts Task #5
6. Upon all major components, DevOps finalizes Task #8
7. Upon all above, Integration Tester starts Task #7
