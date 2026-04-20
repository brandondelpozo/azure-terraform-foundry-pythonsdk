# Project Documentation

## Overview

Azure Durable Functions application (Python 3.11) that orchestrates a multi-agent text processing pipeline. Infrastructure is fully provisioned via Terraform. The pipeline parses text, finds synonyms, and produces an enhanced `.docx` + PDF output.

---

## Project Structure

```
.
├── docs/
│   ├── architecture.md         # Architecture diagrams and component descriptions
│   └── documentation.md        # This file
├── function/
│   ├── agents/
│   │   ├── parse_text_agent.py         # Agent 1: text analysis
│   │   ├── find_equivalents_agent.py   # Agent 2: synonym discovery
│   │   └── consolidate_text_agent.py   # Agent 3: text enhancement + PDF
│   ├── function_app.py                 # All Azure Function triggers
│   ├── host.json
│   └── requirements.txt
├── utilities-functions/
│   └── pdf_converter.py
├── main.tf         # Azure resources
├── variables.tf
├── outputs.tf
├── providers.tf
└── terraform.tfvars
```

---

## Infrastructure

Provisioned with Terraform (AzureRM `~> 3.100`, requires `>= 1.3.0`).

| Resource | Name | Notes |
|---|---|---|
| Resource Group | `rg-testfoundry3-endpoint` | Region: `australiaeast` |
| Storage Account | `stfoundry3endpoint` | Standard LRS; hosts task hub, uploads/, results/ |
| Blob Container | `uploads` | Private; receives client-uploaded files |
| Blob Container | `results` | Private; stores pipeline output |
| Service Plan | `plan-func-testfoundry3-endpoint` | Linux, Consumption (Y1) |
| Function App | `func-testfoundry3-endpoint` | Python 3.11, zip-deployed |
| Azure OpenAI | `testfoundry3-endpoint` | Cognitive Services S0 |
| Model Deployment | `gpt-5.4-nano` | GlobalStandard, 250K TPM, version `2026-03-17` |
| Application Insights | `appi-func-testfoundry3-endpoint` | Linked to managed Log Analytics workspace |

### Terraform Commands

```bash
terraform init
terraform plan
terraform apply
terraform destroy
```

### Key Outputs

| Output | Description |
|---|---|
| `function_app_url` | Function App hostname |
| `openai_endpoint` | Azure OpenAI base URL |
| `openai_chat_completions_endpoint` | Ready-to-use chat completions URL |
| `openai_primary_key` | Sensitive — access key |

---

## Environment Variables (Function App)

| Variable | Source |
|---|---|
| `FUNCTIONS_WORKER_RUNTIME` | `python` |
| `AzureWebJobsStorage` | Storage account connection string |
| `OPENAI_ENDPOINT` | Azure OpenAI endpoint |
| `OPENAI_API_KEY` | Azure OpenAI primary key |
| `OPENAI_MODEL` | Model deployment name (`gpt-5.4-nano`) |
| `STORAGE_ACCOUNT_NAME` | Storage account name |
| `STORAGE_ACCOUNT_KEY` | Storage account primary key |

---

## Agent Pipeline

All three agents share an `AgentState` TypedDict and are chained sequentially.

```python
AgentState = {
    "text": str,           # raw input text
    "parsed_data": dict,   # output of parse_text_agent
    "synonyms": dict,      # output of find_equivalents_agent
    "enhanced_text": str,  # output of consolidate_text_agent
    "pdf_content": str,    # base64-encoded PDF
}
```

### Agent 1 — `parse_text_agent`

Analyzes the input text and populates `parsed_data`:

- `word_count`, `sentence_count`, `text_length`
- `paragraphs` — list split on `\n\n`

### Agent 2 — `find_equivalents_agent`

Scans words against a built-in synonym map and populates `synonyms`:

```
good → [excellent, great, outstanding]
bad  → [poor, terrible, awful]
big  → [large, huge, enormous]
...
```

### Agent 3 — `consolidate_text_agent`

- Replaces matched words with the first synonym from each list → `enhanced_text`
- Generates a PDF (ReportLab) with original and enhanced sections → `pdf_content` (base64)
- In blob-trigger path: saves `_improved.docx` and `.metadata.json` to `results/`

---

## API Reference

### Path A — Synchronous

**`POST /api/process-text`**

```json
// Request
{ "text": "This is a good example." }

// Response 200
{
  "success": true,
  "original_text": "...",
  "enhanced_text": "...",
  "synonyms_found": 1,
  "pdf_base64": "<base64>",
  "parsed_data": { "word_count": 5, "sentence_count": 1, ... },
  "workflow_info": { "workflow_type": "http_sync_primary", "version": "2.1" }
}
```

---

### Path B — Asynchronous (Durable Functions)

**`POST /api/orchestrators/<orchestrator_name>`**

Returns `202 Accepted` with status/result polling URLs. The orchestrator `text_processing_orchestrator` fans out to three activity functions in sequence:

1. `parse_text_activity`
2. `find_equivalents_activity`
3. `consolidate_text_activity`

---

### Path C — SAS Upload + Blob Trigger

**Step 1 — Request a SAS URL**

**`POST /api/generate-upload-url`**

```json
// Request
{ "filename": "mydoc.txt" }   // .txt or .docx only

// Response 200
{
  "sas_url": "https://<account>.blob.core.windows.net/uploads/mydoc.txt?<sas>",
  "blob_name": "mydoc.txt",
  "container": "uploads",
  "expires_in_minutes": 15
}
```

**Step 2 — Upload the file**

```
PUT <sas_url>
Content-Type: text/plain (or application/vnd.openxmlformats-officedocument.wordprocessingml.document)
Body: <file bytes>
```

No Azure credentials required. SAS token grants write+create only, expires in 15 minutes.

**Step 3 — Automatic processing**

The Blob Trigger fires on `uploads/{name}`, extracts text (`.txt` decoded as UTF-8, `.docx` parsed with `python-docx`), runs the agent pipeline, and writes to `results/`:

- `results/<base>_improved.docx`
- `results/<base>.metadata.json`

---

## Dependencies

```
azure-functions
azure-functions-durable >= 1.0.0
azure-storage-blob >= 12.0.0
langgraph >= 0.0.40
langchain-core >= 0.1.0
reportlab >= 4.0.0
python-docx >= 1.1.0
requests
nltk >= 3.8
textstat >= 0.7.0
PyPDF2 >= 3.0.0
weasyprint >= 60.0
```

---

## Local Development

```bash
cd function
pip install -r requirements.txt
func start
```

> Requires [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local) and a `local.settings.json` with the environment variables listed above.

---

## Deployment

Terraform zips the `function/` directory and deploys it via `zip_deploy_file`:

```bash
terraform apply   # packages + deploys in one step
```

To redeploy the function code only (without reprovisioning infrastructure):

```bash
cd function && zip -r ../function.zip . && cd ..
az functionapp deployment source config-zip \
  --resource-group rg-testfoundry3-endpoint \
  --name func-testfoundry3-endpoint \
  --src function.zip
```
