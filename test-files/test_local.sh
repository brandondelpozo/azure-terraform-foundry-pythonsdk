#!/bin/bash

echo "🧪 Testing local Azure Function..."
echo ""
echo "⚠️  Make sure the function is running in another terminal with: cd function && func start"
echo ""
sleep 2

# Test 1: Process Text Endpoint
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Test 1: Testing /api/process-text endpoint..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

curl -X POST http://localhost:7071/api/process-text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "AI will revolutionize the future of work and business operations. This technology will help companies improve their processes and manage their resources effectively.",
    "filename": "local_test.txt"
  }' 2>/dev/null | jq '.'

echo ""
echo "✅ Test 1 complete!"
echo ""
echo "🔍 Check the function terminal for detailed logs including:"
echo "   - Token usage (prompt_tokens, completion_tokens, total_tokens)"
echo "   - Synonyms found"
echo "   - LangGraph pipeline execution"
echo ""
sleep 2

# Test 2: Generate Upload URL
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Test 2: Testing /api/generate-upload-url endpoint..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

curl -X POST http://localhost:7071/api/generate-upload-url \
  -H "Content-Type: application/json" \
  -d '{"filename": "test_local.docx"}' 2>/dev/null | jq '.'

echo ""
echo "✅ Test 2 complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All tests completed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 Expected in the response:"
echo "   - success: true"
echo "   - token_usage: {prompt_tokens, completion_tokens, total_tokens}"
echo "   - synonyms_found: <number>"
echo "   - enhanced_text: <improved text>"
echo ""
