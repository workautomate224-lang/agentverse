#!/bin/bash
# =============================================================================
# Step 3.1 Railway Key Fix Script
# =============================================================================
# This script fixes the STAGING_OPS_API_KEY mismatch between local and Railway
#
# Run this script interactively:
#   ./FIX_RAILWAY_KEY.sh
#
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=============================================${NC}"
echo -e "${CYAN}  Step 3.1 Railway Key Fix Script${NC}"
echo -e "${CYAN}=============================================${NC}"
echo ""

# Step 1: Check Railway CLI
echo -e "${YELLOW}Step 1: Checking Railway CLI...${NC}"
if ! command -v railway &> /dev/null; then
    echo -e "${RED}Railway CLI not installed. Install it:${NC}"
    echo "  npm install -g @railway/cli"
    exit 1
fi
echo -e "${GREEN}  Railway CLI found${NC}"

# Step 2: Check auth
echo -e "${YELLOW}Step 2: Checking Railway authentication...${NC}"
if ! railway whoami &> /dev/null; then
    echo -e "${YELLOW}  Not logged in. Logging in now...${NC}"
    railway login
fi
echo -e "${GREEN}  Authenticated as: $(railway whoami)${NC}"

# Step 3: Link to project
echo -e "${YELLOW}Step 3: Linking to staging project...${NC}"
PROJECT_ID="30cf5498-5aeb-4cf6-b35c-5ba0b9ed81f2"

# Change to the apps/api directory for linking
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$API_DIR"

echo "  Working directory: $(pwd)"
railway link "$PROJECT_ID" 2>/dev/null || true

# List available services
echo -e "${YELLOW}Step 4: Listing services...${NC}"
railway service || echo "  Run: railway service to select a service"

# Set the key value
KEY_VALUE="staging-ops-step3-key-2026"

echo ""
echo -e "${YELLOW}Step 5: Setting STAGING_OPS_API_KEY...${NC}"
echo -e "  Key value: ${CYAN}$KEY_VALUE${NC}"
echo ""

# Set on API service
echo -e "${YELLOW}Setting on API service...${NC}"
echo "  Run: railway service agentverse-api-staging"
echo "       railway variables set STAGING_OPS_API_KEY=$KEY_VALUE"

# Set on Worker service
echo ""
echo -e "${YELLOW}Setting on Worker service...${NC}"
echo "  Run: railway service agentverse-worker-staging"
echo "       railway variables set STAGING_OPS_API_KEY=$KEY_VALUE"

echo ""
echo -e "${CYAN}=============================================${NC}"
echo -e "${CYAN}  Manual Commands (if automatic fails)${NC}"
echo -e "${CYAN}=============================================${NC}"
echo ""
echo "1. Login to Railway:"
echo "   railway login"
echo ""
echo "2. Link to project:"
echo "   railway link $PROJECT_ID"
echo ""
echo "3. Set API key on API service:"
echo "   railway service agentverse-api-staging"
echo "   railway variables set STAGING_OPS_API_KEY=$KEY_VALUE"
echo ""
echo "4. Set API key on Worker service:"
echo "   railway service agentverse-worker-staging"
echo "   railway variables set STAGING_OPS_API_KEY=$KEY_VALUE"
echo ""
echo "5. Verify the key:"
echo "   curl -s -X GET 'https://agentverse-api-staging-production.up.railway.app/api/v1/ops/chaos/worker-status' \\"
echo "     -H 'X-API-Key: $KEY_VALUE'"
echo ""
echo "6. Run Step 3.1 validation:"
echo "   cd $SCRIPT_DIR"
echo "   STAGING_OPS_API_KEY=$KEY_VALUE python step3_1_e2e_runner.py"
echo ""
echo -e "${GREEN}After setting the key, the API should return worker status instead of 'Invalid staging API key'${NC}"
