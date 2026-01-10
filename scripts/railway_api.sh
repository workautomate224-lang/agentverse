#!/bin/bash
# Railway API Helper Script
# Usage: ./railway_api.sh <query>

TOKEN=$(jq -r '.user.token' ~/.railway/config.json)
QUERY="$1"

curl -s -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST https://backboard.railway.app/graphql/v2 \
     -d "{\"query\": \"$QUERY\"}"
