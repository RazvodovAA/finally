#!/bin/bash
# E2E Test Runner

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "FinAlly E2E Test Runner"
echo "======================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

# Print usage
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    cat << EOF
Usage: ./test/run.sh [OPTIONS]

OPTIONS:
  --docker        Run tests in Docker containers (default)
  --local         Run tests locally (requires npm install)
  --headed        Run with browser visible (local mode)
  --ui            Run Playwright UI mode (local mode)
  --debug         Run in debug mode (local mode)
  --clean         Clean up Docker containers and volumes
  --help          Show this message

EXAMPLES:
  ./test/run.sh                    # Run tests in Docker
  ./test/run.sh --local            # Run tests locally
  ./test/run.sh --local --headed   # Run tests locally with browser visible
  ./test/run.sh --clean            # Clean up Docker
EOF
    exit 0
fi

# Parse options
MODE="docker"
DOCKER_MODE=true
LOCAL_MODE=false
HEADED=false
UI=false
DEBUG=false
CLEAN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            DOCKER_MODE=false
            LOCAL_MODE=true
            shift
            ;;
        --headed)
            HEADED=true
            shift
            ;;
        --ui)
            UI=true
            shift
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Clean mode
if [ "$CLEAN" = true ]; then
    echo "Cleaning up Docker containers and volumes..."
    docker compose -f "$SCRIPT_DIR/docker-compose.test.yml" down -v
    echo "Done!"
    exit 0
fi

# Docker mode
if [ "$DOCKER_MODE" = true ]; then
    echo "Running tests in Docker..."
    echo ""
    cd "$SCRIPT_DIR"
    docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
    RESULT=$?

    echo ""
    if [ $RESULT -eq 0 ]; then
        echo "Tests PASSED"
    else
        echo "Tests FAILED"
    fi

    exit $RESULT
fi

# Local mode
if [ "$LOCAL_MODE" = true ]; then
    echo "Running tests locally..."
    echo ""

    # Check npm
    if ! command -v npm &> /dev/null; then
        echo "Error: npm is not installed. Cannot run tests locally."
        echo "Install Node.js or use --docker mode."
        exit 1
    fi

    cd "$SCRIPT_DIR"

    # Install dependencies
    echo "Installing dependencies..."
    npm install
    echo ""

    # Run tests based on options
    if [ "$UI" = true ]; then
        echo "Starting Playwright UI..."
        npx playwright test --ui
    elif [ "$DEBUG" = true ]; then
        echo "Starting Playwright Debug Mode..."
        npx playwright test --debug
    elif [ "$HEADED" = true ]; then
        echo "Running tests with browser visible..."
        npx playwright test --headed
    else
        echo "Running tests headless..."
        npx playwright test
    fi

    RESULT=$?
    echo ""
    if [ $RESULT -eq 0 ]; then
        echo "Tests PASSED"
        echo "View report: npx playwright show-report"
    else
        echo "Tests FAILED"
        echo "View report: npx playwright show-report"
    fi

    exit $RESULT
fi
