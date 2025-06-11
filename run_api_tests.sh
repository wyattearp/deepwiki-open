#!/usr/bin/env bash
set -e

# Start services via Docker Compose
docker compose up -d

# Base URL
API_URL=${API_URL:-http://localhost:${PORT:-8001}}

echo "Waiting for API to be healthy at $API_URL/health"
until curl -s -f "$API_URL/health" > /dev/null; do
  sleep 2
done

echo "Running integration tests..."
python -m unittest api/test_api_integration.py
