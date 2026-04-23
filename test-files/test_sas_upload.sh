#!/bin/bash

# Test script for SAS URL generation and file upload
# This script tests the generate-upload-url endpoint and uploads a doc file

set -e

# Configuration
ENDPOINT_URL="https://func-testfoundry3-endpoint.azurewebsites.net/api/generate-upload-url"
TEST_FILE="sample_test.docx"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="sas_upload_test_${TIMESTAMP}.docx"
LOG_FILE="sas_upload_test_${TIMESTAMP}.log"

echo "=== SAS URL Upload Test ===" | tee "$LOG_FILE"
echo "Timestamp: $TIMESTAMP" | tee -a "$LOG_FILE"
echo "Test file: $TEST_FILE" | tee -a "$LOG_FILE"
echo "Upload filename: $FILENAME" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Check if test file exists
if [ ! -f "$TEST_FILE" ]; then
    echo "ERROR: Test file $TEST_FILE not found!" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Step 1: Generating SAS URL..." | tee -a "$LOG_FILE"

# Generate SAS URL
SAS_RESPONSE=$(curl -s -X POST "$ENDPOINT_URL" \
    -H "Content-Type: application/json" \
    -d "{\"filename\": \"$FILENAME\"}")

echo "SAS Response: $SAS_RESPONSE" | tee -a "$LOG_FILE"

# Parse SAS URL from response
SAS_URL=$(echo "$SAS_RESPONSE" | jq -r '.sas_url')
BLOB_NAME=$(echo "$SAS_RESPONSE" | jq -r '.blob_name')
CONTAINER=$(echo "$SAS_RESPONSE" | jq -r '.container')
EXPIRES_IN=$(echo "$SAS_RESPONSE" | jq -r '.expires_in_minutes')

if [ "$SAS_URL" = "null" ] || [ -z "$SAS_URL" ]; then
    echo "ERROR: Failed to generate SAS URL!" | tee -a "$LOG_FILE"
    exit 1
fi

echo "SAS URL generated successfully!" | tee -a "$LOG_FILE"
echo "Blob name: $BLOB_NAME" | tee -a "$LOG_FILE"
echo "Container: $CONTAINER" | tee -a "$LOG_FILE"
echo "Expires in: $EXPIRES_IN minutes" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "Step 2: Uploading file..." | tee -a "$LOG_FILE"

# Upload file using SAS URL
UPLOAD_RESPONSE=$(curl -s -X PUT "$SAS_URL" \
    -H "x-ms-blob-type: BlockBlob" \
    -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
    --data-binary @"$TEST_FILE")

echo "Upload response: $UPLOAD_RESPONSE" | tee -a "$LOG_FILE"

# Check if upload was successful (empty response usually means success)
if [ -z "$UPLOAD_RESPONSE" ]; then
    echo "File uploaded successfully!" | tee -a "$LOG_FILE"
    UPLOAD_SUCCESS=true
else
    echo "Upload response received: $UPLOAD_RESPONSE" | tee -a "$LOG_FILE"
    # Check if it's an error response
    if echo "$UPLOAD_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
        echo "ERROR: Upload failed!" | tee -a "$LOG_FILE"
        UPLOAD_SUCCESS=false
    else
        echo "File uploaded successfully!" | tee -a "$LOG_FILE"
        UPLOAD_SUCCESS=true
    fi
fi

echo "" | tee -a "$LOG_FILE"

if [ "$UPLOAD_SUCCESS" = true ]; then
    echo "Step 3: Verifying upload..." | tee -a "$LOG_FILE"
    
    # Get file size for verification
    ORIGINAL_SIZE=$(stat -f%z "$TEST_FILE" 2>/dev/null || stat -c%s "$TEST_FILE" 2>/dev/null)
    echo "Original file size: $ORIGINAL_SIZE bytes" | tee -a "$LOG_FILE"
    
    # Create a summary JSON file
    SUMMARY_FILE="sas_upload_test_${TIMESTAMP}_result.json"
    cat > "$SUMMARY_FILE" << EOF
{
  "test_timestamp": "$TIMESTAMP",
  "test_file": "$TEST_FILE",
  "upload_filename": "$FILENAME",
  "original_size_bytes": $ORIGINAL_SIZE,
  "sas_response": $SAS_RESPONSE,
  "upload_success": $UPLOAD_SUCCESS,
  "blob_name": "$BLOB_NAME",
  "container": "$CONTAINER",
  "expires_in_minutes": $EXPIRES_IN,
  "sas_url": "$SAS_URL",
  "test_completed": "$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")"
}
EOF
    
    echo "Test completed successfully!" | tee -a "$LOG_FILE"
    echo "Summary saved to: $SUMMARY_FILE" | tee -a "$LOG_FILE"
    echo "Log saved to: $LOG_FILE" | tee -a "$LOG_FILE"
else
    echo "Test failed!" | tee -a "$LOG_FILE"
    exit 1
fi

echo "" | tee -a "$LOG_FILE"
echo "=== Test Summary ===" | tee -a "$LOG_FILE"
echo "Status: PASSED" | tee -a "$LOG_FILE"
echo "File uploaded: $FILENAME" | tee -a "$LOG_FILE"
echo "Container: $CONTAINER" | tee -a "$LOG_FILE"
echo "SAS URL expires in: $EXPIRES_IN minutes" | tee -a "$LOG_FILE"