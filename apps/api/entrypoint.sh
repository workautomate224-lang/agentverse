#!/bin/bash
# Universal entrypoint for AgentVerse API/Worker
# Set MODE=worker for Celery worker, otherwise runs API

set -e

echo "=== AgentVerse Container Startup ==="
echo "Environment: ${ENVIRONMENT:-development}"
echo "Mode: ${MODE:-api}"

if [ "${MODE}" = "worker" ]; then
    echo "Starting as Celery Worker with Beat scheduler..."
    exec ./start-worker.sh
else
    echo "Starting as API server..."
    exec ./start.sh
fi
