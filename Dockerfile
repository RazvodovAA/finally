# Multi-stage build: Node 20 (frontend) -> Python 3.12 (backend + serving)

# Stage 1: Build Next.js frontend (static export)
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Copy frontend source (if it exists)
COPY frontend/ .

# Install dependencies and build
RUN npm install
RUN npm run build

# Stage 2: Python runtime with FastAPI backend
FROM python:3.12-slim

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy Python backend
COPY backend/ .

# Install Python dependencies via uv
RUN uv sync --frozen

# Copy built frontend static export from stage 1
# Next.js 13+ outputs to 'out/' directory
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

# Create db directory for SQLite volume mount
RUN mkdir -p /app/db

# Expose port 8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health').read()" || exit 1

# Start FastAPI server
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
