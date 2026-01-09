#!/bin/bash
set -e

echo "=== AgentVerse Frontend Fix Script ==="

# Navigate to web directory
cd /Users/mac/Desktop/simulation/agentverse/apps/web

echo "1. Removing nested web/web folder..."
rm -rf web

echo "2. Removing old node_modules and lock files..."
rm -rf node_modules
rm -f package-lock.json

echo "3. Installing dependencies..."
npm install

echo "4. Starting dev server on port 3001..."
echo ""
echo "=== Server starting! Open http://localhost:3001 ==="
echo ""
npm run dev -- -p 3001
