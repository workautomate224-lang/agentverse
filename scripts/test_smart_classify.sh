#!/bin/bash
# Test Smart Auto-Classification for Temporal Test API
# This script tests different prompts to verify auto-classification works correctly

API_URL="${1:-http://localhost:3000/api/temporal-test}"

echo "========================================"
echo "Testing Smart Auto-Classification"
echo "API URL: $API_URL"
echo "========================================"

# Test 1: Should auto-enable web search (current events question)
echo ""
echo "=== TEST 1: Web Search Auto-Trigger ==="
echo "Question: What is Tesla stock price today?"
echo ""
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is Tesla stock price today?",
    "enable_isolation": false
  }' | jq '{
    question: "What is Tesla stock price today?",
    auto_classify_enabled,
    classification,
    web_search_enabled,
    thinking_mode_enabled
  }'

# Test 2: Should auto-enable thinking mode (analysis question)
echo ""
echo "=== TEST 2: Thinking Mode Auto-Trigger ==="
echo "Question: Analyze the pros and cons of electric vehicles vs hydrogen fuel cells"
echo ""
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Analyze the pros and cons of electric vehicles vs hydrogen fuel cells",
    "enable_isolation": false
  }' | jq '{
    question: "Analyze the pros and cons of electric vehicles vs hydrogen fuel cells",
    auto_classify_enabled,
    classification,
    web_search_enabled,
    thinking_mode_enabled
  }'

# Test 3: Should auto-enable BOTH (current events + analysis)
echo ""
echo "=== TEST 3: Both Auto-Trigger ==="
echo "Question: Analyze the latest news about AI regulation and its potential impact"
echo ""
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Analyze the latest news about AI regulation and its potential impact",
    "enable_isolation": false
  }' | jq '{
    question: "Analyze the latest news about AI regulation and its potential impact",
    auto_classify_enabled,
    classification,
    web_search_enabled,
    thinking_mode_enabled
  }'

# Test 4: Should NOT trigger either (simple factual question)
echo ""
echo "=== TEST 4: No Auto-Trigger ==="
echo "Question: What is the capital of France?"
echo ""
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the capital of France?",
    "enable_isolation": false
  }' | jq '{
    question: "What is the capital of France?",
    auto_classify_enabled,
    classification,
    web_search_enabled,
    thinking_mode_enabled
  }'

# Test 5: Manual override - force web_search OFF even for current events
echo ""
echo "=== TEST 5: Manual Override (web_search: false) ==="
echo "Question: What is Tesla stock price today? (with manual web_search=false)"
echo ""
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is Tesla stock price today?",
    "enable_isolation": false,
    "web_search": false
  }' | jq '{
    question: "What is Tesla stock price today? (manual override)",
    auto_classify_enabled,
    classification,
    manual_web_search,
    web_search_enabled,
    thinking_mode_enabled
  }'

# Test 6: Auto-classify disabled
echo ""
echo "=== TEST 6: Auto-Classify Disabled ==="
echo "Question: What is the latest news about Tesla? (with auto_classify=false)"
echo ""
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the latest news about Tesla?",
    "enable_isolation": false,
    "auto_classify": false
  }' | jq '{
    question: "What is the latest news about Tesla? (auto_classify=false)",
    auto_classify_enabled,
    classification,
    web_search_enabled,
    thinking_mode_enabled
  }'

echo ""
echo "========================================"
echo "Tests completed!"
echo "========================================"
