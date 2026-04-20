# FinAlly — AI Trading Workstation

AI-powered trading platform with live market data, portfolio management, and LLM chat assistant for trade execution.

## Quick Start

```bash
bash scripts/start_mac.sh          # macOS/Linux
powershell scripts/start_windows.ps1  # Windows
```

Opens at `http://localhost:8000` with $10,000 virtual cash and 10 default tickers.

## Setup

Create `.env`:
```bash
OPENAI_API_KEY=your-api-key
MASSIVE_API_KEY=          # optional: real market data
LLM_MOCK=false            # optional: mock LLM for testing
```

## Stack

- **Frontend**: Next.js (TypeScript, static export)
- **Backend**: FastAPI (Python, uv)
- **Database**: SQLite (persistent)
- **Real-time**: SSE price streams + LLM chat

## Docs

See `planning/PLAN.md` for full specification and architecture.
