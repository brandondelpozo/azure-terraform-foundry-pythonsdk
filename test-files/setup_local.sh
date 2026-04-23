#!/bin/bash

echo "🔧 Setting up local Azure Functions environment..."

# Get OpenAI Key
echo "📝 Fetching OpenAI API Key..."
OPENAI_KEY=$(az cognitiveservices account keys list \
  --name testfoundry3-endpoint \
  --resource-group rg-testfoundry3-endpoint \
  --query "key1" -o tsv)

# Get Storage Key
echo "📝 Fetching Storage Account Key..."
STORAGE_KEY=$(az storage account keys list \
  --account-name stfoundry3endpoint \
  --resource-group rg-testfoundry3-endpoint \
  --query "[0].value" -o tsv)

# Build Storage Connection String
STORAGE_CONNECTION="DefaultEndpointsProtocol=https;AccountName=stfoundry3endpoint;AccountKey=${STORAGE_KEY};EndpointSuffix=core.windows.net"

# Create local.settings.json
echo "📄 Creating local.settings.json..."
cat > function/local.settings.json << SETTINGS
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "${STORAGE_CONNECTION}",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "OPENAI_ENDPOINT": "https://australiaeast.api.cognitive.microsoft.com/",
    "OPENAI_API_KEY": "${OPENAI_KEY}",
    "OPENAI_MODEL": "gpt-5.4-nano",
    "STORAGE_ACCOUNT_NAME": "stfoundry3endpoint",
    "STORAGE_ACCOUNT_KEY": "${STORAGE_KEY}"
  }
}
SETTINGS

echo "✅ local.settings.json created successfully!"
echo ""
echo "📦 Installing Python dependencies..."
cd function
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To start the function locally, run:"
echo "   cd function"
echo "   func start"
echo ""
echo "🧪 To test the endpoint, run (in another terminal):"
echo "   ./test_local.sh"
