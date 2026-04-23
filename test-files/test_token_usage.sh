#!/bin/bash

echo "🔍 Quick Token Usage Test"
echo ""

RESPONSE=$(curl -s -X POST http://localhost:7071/api/process-text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "AI will transform work",
    "filename": "quick_test.txt"
  }')

echo "Response:"
echo "$RESPONSE" | jq '.'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Token Usage Extracted:"
echo "$RESPONSE" | jq '.token_usage'

echo ""
echo "Synonyms Found:"
echo "$RESPONSE" | jq '.synonyms_found'

echo ""
echo "Success Status:"
echo "$RESPONSE" | jq '.success'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
