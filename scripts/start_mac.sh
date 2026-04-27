#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER_NAME="finally-app"
IMAGE_NAME="finally:latest"
BUILD_FLAG="${1:-}"

echo "FinAlly Startup Script"
echo "====================="
echo ""

# Check if .env file exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "Error: .env file not found at $PROJECT_DIR/.env"
    echo "Please create .env from .env.example and add your API keys."
    exit 1
fi

# Check if image needs to be built
if [ "$BUILD_FLAG" = "--build" ] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "Building Docker image..."
    docker build -t "$IMAGE_NAME" "$PROJECT_DIR"
    echo "Docker image built successfully."
    echo ""
fi

# Check if container is already running
if docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME\$"; then
    echo "Container '$CONTAINER_NAME' is already running."
    echo ""
    echo "FinAlly is running at http://localhost:8000"
    exit 0
fi

# Check if container exists but is stopped
if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME\$"; then
    echo "Starting existing container..."
    docker start "$CONTAINER_NAME"
else
    echo "Starting new container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p 8000:8000 \
        -v finally-data:/app/db \
        --env-file "$PROJECT_DIR/.env" \
        -e PYTHONUNBUFFERED=1 \
        --restart unless-stopped \
        "$IMAGE_NAME"
fi

# Wait for container to be healthy
echo "Waiting for FinAlly to be ready..."
for i in {1..30}; do
    if docker exec "$CONTAINER_NAME" curl -s http://localhost:8000/api/health &>/dev/null; then
        echo ""
        echo "FinAlly is running at http://localhost:8000"
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo ""
echo "Warning: Health check timed out, but container may still be starting."
echo "FinAlly should be available at http://localhost:8000"
echo ""
echo "To view logs: docker logs -f $CONTAINER_NAME"
