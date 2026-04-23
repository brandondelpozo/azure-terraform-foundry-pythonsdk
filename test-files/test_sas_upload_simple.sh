#!/bin/bash

# Simple SAS URL upload test using curl commands only
# This is a minimal version for quick testing

echo "=== Simple SAS Upload Test ==="

# Generate SAS URL
echo "Generating SAS URL..."
SAS_RESPONSE=$(curl -s -X POST "https://func-testfoundry3-endpoint.azurewebsites.net/api/generate-upload-url" \
    -H "Content-Type: application/json" \
    -d '{"filename": "simple_test.docx"}')

echo "SAS Response: $SAS_RESPONSE"

# Extract SAS URL
SAS_URL=$(echo "$SAS_RESPONSE" | jq -r '.sas_url')

if [ "$SAS_URL" = "null" ] || [ -z "$SAS_URL" ]; then
    echo "ERROR: Failed to generate SAS URL!"
    exit 1
fi

echo "Uploading file..."
# Upload file
curl -X PUT "$SAS_URL" \
    -H "x-ms-blob-type: BlockBlob" \
    -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
    --data-binary @sample_test.docx

echo ""
echo "Upload completed!"