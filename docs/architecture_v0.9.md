# Architecture Diagram

## Overview

This solution is an **Azure Durable Functions** application (Python 3.11) deployed via **Terraform** that orchestrates a multi-agent text processing pipeline. The agents follow a **LangGraph-style** sequential state graph pattern, passing a shared `AgentState` object through each node.

---

## Architecture Diagram

```mermaid
flowchart TD
    %% ─── External Client ───────────────────────────────────────────────
    Client(["🌐 HTTP Client"])

    %% ─── Azure Infrastructure (Terraform-provisioned) ──────────────────
    subgraph Azure["☁️ Azure (Terraform-provisioned)"]

        subgraph RG["📦 Resource Group"]

            subgraph FunctionApp["⚡ Azure Linux Function App (Python 3.11 · Consumption Y1)"]

                %% ── Entry Points ──────────────────────────────────────
                subgraph Triggers["🔌 Triggers / Entry Points"]
                    HTTP["HTTP Trigger\nPOST /process-text\n(sync – primary)"]
                    DurableHTTP["HTTP Trigger\nPOST /orchestrators/...\n(async – durable start)"]
                end

                %% ── Durable Functions Layer ───────────────────────────
                subgraph DurableLayer["🔄 Azure Durable Functions"]
                    Orchestrator["Orchestrator Function\ntext_processing_orchestrator\n(manages workflow state &\nactivity fan-out/fan-in)"]

                    subgraph Activities["📋 Activity Functions"]
                        A1["parse_text_activity"]
                        A2["find_equivalents_activity"]
                        A3["consolidate_text_activity"]
                    end
                end

                %% ── LangGraph Agent Pipeline ──────────────────────────
                subgraph LangGraph["🦜 LangGraph-style Agent Pipeline\n(Sequential State Graph)"]
                    direction LR
                    State0(["AgentState\n{ text, parsed_data,\n  synonyms, enhanced_text,\n  pdf_content }"])

                    subgraph Node1["Node 1"]
                        Agent1["parse_text_agent\n─────────────\n• word count\n• sentence count\n• paragraph split"]
                    end

                    subgraph Node2["Node 2"]
                        Agent2["find_equivalents_agent\n─────────────\n• synonym lookup\n• word matching"]
                    end

                    subgraph Node3["Node 3"]
                        Agent3["consolidate_text_agent\n─────────────\n• apply synonyms\n• generate PDF (ReportLab)\n• base64 encode"]
                    end

                    State0 --> Agent1 --> Agent2 --> Agent3
                end
            end

            %% ── Storage Account ───────────────────────────────────────
            Storage[("🗄️ Azure Storage Account\n(LRS)\n• Function state\n• Durable task hub\n• Deployment zip")]

            %% ── Azure OpenAI ──────────────────────────────────────────
            subgraph OpenAI["🤖 Azure OpenAI (Cognitive Services S0)"]
                GPT["Model Deployment\ngpt-5.4-nano\n(GlobalStandard)"]
            end

        end
    end

    %% ─── Terraform (IaC) ───────────────────────────────────────────────
    Terraform["🏗️ Terraform\n(IaC)\n• Resource Group\n• Storage Account\n• Service Plan\n• Function App\n• OpenAI Account\n• Model Deployment\n• zip_deploy_file"]

    %% ─── Connections ────────────────────────────────────────────────────

    %% Client → Function App
    Client -->|"POST /process-text\n{ text: '...' }"| HTTP
    Client -->|"POST /orchestrators/...\n{ text: '...' }"| DurableHTTP

    %% Sync path (HTTP trigger calls agents directly)
    HTTP -->|"direct call\n(no Durable)"| Node1
    Node1 --> Node2
    Node2 --> Node3
    Node3 -->|"JSON response\n{ enhanced_text, pdf_base64, ... }"| HTTP
    HTTP -->|"200 OK"| Client

    %% Async / Durable path
    DurableHTTP -->|"start_new()"| Orchestrator
    Orchestrator -->|"call_activity()\nStep 1"| A1
    A1 -->|"invoke"| Agent1
    Orchestrator -->|"call_activity()\nStep 2"| A2
    A2 -->|"invoke"| Agent2
    Orchestrator -->|"call_activity()\nStep 3"| A3
    A3 -->|"invoke"| Agent3
    Orchestrator -->|"check_status_response\n(202 + polling URLs)"| Client

    %% Storage
    FunctionApp <-->|"state persistence\ntask hub"| Storage

    %% OpenAI (available via env vars)
    FunctionApp -.->|"OPENAI_ENDPOINT\nOPENAI_API_KEY\nOPENAI_MODEL (env vars)"| GPT

    %% Terraform provisions everything
    Terraform -.->|"provisions"| RG

    %% ─── Styles ─────────────────────────────────────────────────────────
    classDef azure    fill:#0078D4,color:#fff,stroke:#005a9e
    classDef durable  fill:#7B2FBE,color:#fff,stroke:#5a1f8a
    classDef agent    fill:#107C10,color:#fff,stroke:#0a5c0a
    classDef storage  fill:#F25022,color:#fff,stroke:#b33c19
    classDef openai   fill:#FF8C00,color:#fff,stroke:#cc7000
    classDef tf       fill:#5C4EE5,color:#fff,stroke:#3d35b0
    classDef client   fill:#555,color:#fff,stroke:#333
    classDef state    fill:#e8f4fd,color:#333,stroke:#0078D4

    class HTTP,DurableHTTP azure
    class Orchestrator,A1,A2,A3 durable
    class Agent1,Agent2,Agent3 agent
    class Storage storage
    class GPT openai
    class Terraform tf
    class Client client
    class State0 state
```

---

## Component Descriptions

| Component | Type | Role |
|---|---|---|
| **HTTP Trigger** `/process-text` | Azure Function | Synchronous entry point — calls agents directly and returns a full JSON response immediately |
| **HTTP Trigger** `/orchestrators/...` | Azure Function | Async entry point — starts a Durable orchestration and returns polling URLs (202) |
| **`text_processing_orchestrator`** | Durable Orchestrator | Manages the sequential workflow; calls each activity in order, maintains state across retries/replays |
| **`parse_text_activity`** | Durable Activity | Wraps `parse_text_agent`; executed as a reliable, retryable unit of work |
| **`find_equivalents_activity`** | Durable Activity | Wraps `find_equivalents_agent`; executed as a reliable, retryable unit of work |
| **`consolidate_text_activity`** | Durable Activity | Wraps `consolidate_text_agent`; executed as a reliable, retryable unit of work |
| **`parse_text_agent`** | LangGraph Node | Analyzes text: word count, sentence count, paragraph split → updates `AgentState.parsed_data` |
| **`find_equivalents_agent`** | LangGraph Node | Finds synonyms for words in the text → updates `AgentState.synonyms` |
| **`consolidate_text_agent`** | LangGraph Node | Applies synonyms, generates a PDF via ReportLab, base64-encodes it → updates `AgentState.enhanced_text` & `pdf_content` |
| **Azure Storage Account** | Infrastructure | Hosts the Durable Task Hub (orchestration state), function deployment zip, and runtime state |
| **Azure OpenAI / gpt-5.4-nano** | AI Service | Available to agents via environment variables (`OPENAI_ENDPOINT`, `OPENAI_API_KEY`, `OPENAI_MODEL`) |
| **Terraform** | IaC | Provisions all Azure resources: Resource Group, Storage, Service Plan, Function App, OpenAI account & model deployment |

---

## Two Execution Paths

### Path A — Synchronous (HTTP Trigger)
```
Client → POST /process-text
       → parse_text_agent
       → find_equivalents_agent
       → consolidate_text_agent
       → 200 OK { enhanced_text, pdf_base64, ... }
```

### Path B — Asynchronous (Durable Functions + LangGraph)
```
Client → POST /orchestrators/...
       → DurableOrchestrationClient.start_new()
       → Orchestrator: call_activity("parse_text_activity")
                     → parse_text_agent (LangGraph Node 1)
       → Orchestrator: call_activity("find_equivalents_activity")
                     → find_equivalents_agent (LangGraph Node 2)
       → Orchestrator: call_activity("consolidate_text_activity")
                     → consolidate_text_agent (LangGraph Node 3)
       → 202 Accepted + status/result polling URLs
```
