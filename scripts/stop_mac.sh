#!/bin/bash

set -e

CONTAINER_NAME="finally-app"

echo "FinAlly Shutdown Script"
echo "====================="
echo ""

# Check if container exists and is running
if docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME\$"; then
    echo "Stopping container '$CONTAINER_NAME'..."
    docker stop "$CONTAINER_NAME"
    docker rm "$CONTAINER_NAME"
    echo "Container stopped and removed."
    echo ""
    echo "Note: Data persists in the 'finally-data' Docker volume."
    echo "To remove the volume and all data, run:"
    echo "  docker volume rm finally-data"
elif docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME\$"; then
    echo "Container '$CONTAINER_NAME' is not running."
    echo "Removing stopped container..."
    docker rm "$CONTAINER_NAME"
    echo "Stopped container removed."
else
    echo "Container '$CONTAINER_NAME' does not exist."
fi
