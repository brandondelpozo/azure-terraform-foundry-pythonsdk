# Local Testing Guide

## Prerequisites

1. **Azure Functions Core Tools** (v4)
   ```bash
   brew tap azure/functions
   brew install azure-functions-core-tools@4
   ```

2. **Azure CLI** (already installed)
   ```bash
   az --version
   ```

3. **Python 3.11**
   ```bash
   python3 --version
   ```

4. **jq** (for JSON parsing in tests)
   ```bash
   brew install jq
   ```

## Quick Start

### Step 1: Setup Local Environment

Run the setup script to fetch Azure credentials and install dependencies:

```bash
chmod +x setup_local.sh
./setup_local.sh
```

This will:
- ✅ Fetch OpenAI API key from Azure
- ✅ Fetch Storage Account key from Azure
- ✅ Create `function/local.settings.json` with credentials
- ✅ Install Python dependencies

### Step 2: Start Function Locally

Open a terminal and run:

```bash
cd function
func start
```

You should see:
```
Azure Functions Core Tools
Core Tools Version: 4.x.x
Function Runtime Version: 4.x.x

Functions:
  generate_upload_url: [POST] http://localhost:7071/api/generate-upload-url
  http_start: [POST] http://localhost:7071/api/process-text
  process_blob: blobTrigger
```

### Step 3: Test the Function

Open **another terminal** and run:

```bash
chmod +x test_local.sh
./test_local.sh
```

Or for a quick token usage test:

```bash
chmod +x test_token_usage.sh
./test_token_usage.sh
```

## Manual Testing

### Test 1: Process Text Endpoint

```bash
curl -X POST http://localhost:7071/api/process-text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "AI will revolutionize the future of work",
    "filename": "test.txt"
  }' | jq '.'
```

**Expected Response:**
```json
{
  "success": true,
  "token_usage": {
    "prompt_tokens": 233,
    "completion_tokens": 676,
    "total_tokens": 909
  },
  "synonyms_found": 41,
  "enhanced_text": "...",
  "workflow_info": {
    "langgraph_enabled": true,
    "azure_openai_chat_completions_enabled": true
  }
}
```

### Test 2: Generate Upload URL

```bash
curl -X POST http://localhost:7071/api/generate-upload-url \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.docx"}' | jq '.'
```

**Expected Response:**
```json
{
  "sas_url": "https://stfoundry3endpoint.blob.core.windows.net/uploads/test.docx?...",
  "blob_name": "test.docx",
  "container": "uploads",
  "expires_in_minutes": 15
}
```

### Test 3: Blob Trigger (Upload File)

Upload a file to the `uploads` container and watch the function logs:

```bash
# Upload a test file
az storage blob upload \
  --account-name stfoundry3endpoint \
  --container-name uploads \
  --name test_local.docx \
  --file test-files/sample_test.docx \
  --auth-mode key
```

Watch the function terminal for processing logs.

## What to Look For

### In Function Logs (Terminal 1):

```
[2026-04-21T14:46:44] Executing 'Functions.process_blob'
[2026-04-21T14:46:44] Starting synonym analysis with Azure OpenAI Chat Completions...
[2026-04-21T14:46:57] Token usage - Prompt: 233, Completion: 676, Total: 909
[2026-04-21T14:46:57] Azure OpenAI Chat Completions found synonyms for 41 words
[2026-04-21T14:46:57] Stored token usage in state: {...}
[2026-04-21T14:46:57] Executed 'Functions.process_blob' (Succeeded, Duration=13290ms)
```

### In Test Response (Terminal 2):

```json
{
  "token_usage": {
    "prompt_tokens": 233,
    "completion_tokens": 676,
    "total_tokens": 909
  }
}
```

## Troubleshooting

### Issue: "Connection refused" error
**Solution:** Make sure `func start` is running in another terminal

### Issue: "Module not found" error
**Solution:** Run `pip install -r requirements.txt` in the function directory

### Issue: "Authentication failed" error
**Solution:** Re-run `./setup_local.sh` to refresh credentials

### Issue: No token usage in response
**Solution:** Check function logs for errors in the OpenAI API call

## Files Created

- `setup_local.sh` - Setup script to configure local environment
- `test_local.sh` - Comprehensive test script
- `test_token_usage.sh` - Quick token usage verification
- `function/local.settings.json` - Local configuration (auto-generated, gitignored)

## Clean Up

To stop the function:
- Press `Ctrl+C` in the terminal running `func start`

To remove local settings:
```bash
rm function/local.settings.json
```

## Next Steps

After successful local testing:
1. Deploy to Azure with `terraform apply`
2. Test the deployed function with the same endpoints (replace localhost with Azure URL)
3. Check metadata files in the `results/` container for token usage
