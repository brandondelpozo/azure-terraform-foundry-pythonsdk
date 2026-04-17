import azure.functions as func
import azure.durable_functions as df
import json
import logging
import os
import traceback
import importlib.util
from io import BytesIO
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from azure.storage.blob import (
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions,
    ContainerClient,
    ContentSettings,
)

from agents.parse_text_agent import parse_text_agent, AgentState
from agents.find_equivalents_agent import find_equivalents_agent
from agents.consolidate_text_agent import consolidate_text_agent

# Configure logging
logging.basicConfig(level=logging.INFO)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _load_pdf_converter():
    """Load pdf converter helper from utilities-functions/pdf_converter.py."""
    repo_root = os.path.dirname(os.path.dirname(__file__))
    converter_path = os.path.join(repo_root, "utilities-functions", "pdf_converter.py")

    spec = importlib.util.spec_from_file_location("pdf_converter", converter_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load pdf converter from {converter_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# ---------------------------------------------------------------------------
# Helper: extract plain text from .txt or .docx bytes
# ---------------------------------------------------------------------------
def _extract_text(blob_bytes: bytes, filename: str) -> str:
    """Extract plain text from .txt or .docx bytes."""
    if filename.endswith(".txt"):
        return blob_bytes.decode("utf-8")
    elif filename.endswith(".docx"):
        import io
        from docx import Document
        logging.info("Parsing .docx content for %s", filename)
        doc = Document(io.BytesIO(blob_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        logging.info("Extracted %d non-empty paragraphs from %s", len(paragraphs), filename)
        return "\n".join(paragraphs)
    else:
        raise ValueError(f"Unsupported file type: {filename}")


# ---------------------------------------------------------------------------
# Helper: run the 3-agent pipeline on a plain text string
# ---------------------------------------------------------------------------
def _run_agent_pipeline(text: str) -> dict:
    initial_state = {
        "text": text,
        "parsed_data": {},
        "synonyms": {},
        "enhanced_text": "",
        "pdf_content": "",
    }
    state1 = parse_text_agent(initial_state)
    state2 = find_equivalents_agent(state1)
    return consolidate_text_agent(state2)


def _build_docx_bytes_from_text(text: str) -> bytes:
    """Build a .docx document from plain text while preserving paragraph breaks."""
    from docx import Document

    document = Document()

    lines = text.split("\n")
    if not lines:
        lines = [text]

    for line in lines:
        document.add_paragraph(line)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# PATH A — Synchronous HTTP Trigger  POST /process-text
# ---------------------------------------------------------------------------
@app.route(route="process-text", methods=["POST"])
def http_start(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger that processes text (synchronous response)."""
    try:
        req_body = req.get_json()
        if not req_body or "text" not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'text' in request body"}),
                status_code=400,
                mimetype="application/json",
            )

        text = req_body.get("text")
        logging.info(f"Processing text from /process-text: {text[:100]}...")

        final_state = _run_agent_pipeline(text)

        response = {
            "success": True,
            "original_text": final_state.get("text", ""),
            "enhanced_text": final_state.get("enhanced_text", ""),
            "synonyms_found": len(final_state.get("synonyms", {})),
            "pdf_base64": final_state.get("pdf_content", ""),
            "parsed_data": final_state.get("parsed_data", {}),
            "workflow_info": {
                "agents_used": ["parse_text", "find_equivalents", "consolidate_text"],
                "workflow_type": "http_sync_primary",
                "version": "2.1",
            },
        }

        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.error(f"HTTP trigger error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


# ---------------------------------------------------------------------------
# PATH B — Async Durable Orchestrator
# ---------------------------------------------------------------------------
@app.orchestration_trigger(context_name="context")
def text_processing_orchestrator(context: df.DurableOrchestrationContext):
    """Orchestrator function that manages the LangGraph workflow"""
    try:
        input_data = context.get_input()
        text = input_data.get("text", "")

        logging.info(f"Orchestrator started for text: {text[:50]}...")

        initial_state = {
            "text": text,
            "parsed_data": {},
            "synonyms": {},
            "enhanced_text": "",
            "pdf_content": "",
        }

        state_after_parse = yield context.call_activity("parse_text_activity", initial_state)
        state_after_equivalents = yield context.call_activity("find_equivalents_activity", state_after_parse)
        final_state = yield context.call_activity("consolidate_text_activity", state_after_equivalents)

        response = {
            "success": True,
            "original_text": final_state.get("text", ""),
            "enhanced_text": final_state.get("enhanced_text", ""),
            "synonyms_found": len(final_state.get("synonyms", {})),
            "pdf_base64": final_state.get("pdf_content", ""),
            "parsed_data": final_state.get("parsed_data", {}),
            "workflow_info": {
                "agents_used": ["parse_text", "find_equivalents", "consolidate_text"],
                "workflow_type": "durable_langgraph_hybrid",
                "version": "2.0",
                "instance_id": context.instance_id,
            },
        }

        logging.info(f"Orchestration completed successfully for instance: {context.instance_id}")
        return response

    except Exception as e:
        logging.error(f"Orchestrator error: {str(e)}")
        return {"error": str(e), "workflow": "durable_langgraph_hybrid"}


# Activity Functions
@app.activity_trigger(input_name="input")
def parse_text_activity(input: dict) -> dict:
    logging.info("Executing parse_text_activity")
    try:
        result = parse_text_agent(input)
        logging.info("parse_text_activity completed successfully")
        return result
    except Exception as e:
        logging.error(f"parse_text_activity error: {str(e)}")
        raise


@app.activity_trigger(input_name="input")
def find_equivalents_activity(input: dict) -> dict:
    logging.info("Executing find_equivalents_activity")
    try:
        result = find_equivalents_agent(input)
        logging.info("find_equivalents_activity completed successfully")
        return result
    except Exception as e:
        logging.error(f"find_equivalents_activity error: {str(e)}")
        raise


@app.activity_trigger(input_name="input")
def consolidate_text_activity(input: dict) -> dict:
    logging.info("Executing consolidate_text_activity")
    try:
        result = consolidate_text_agent(input)
        logging.info("consolidate_text_activity completed successfully")
        return result
    except Exception as e:
        logging.error(f"consolidate_text_activity error: {str(e)}")
        raise


# ---------------------------------------------------------------------------
# PATH C — SAS URL generation  POST /generate-upload-url  (NEW)
# ---------------------------------------------------------------------------
@app.route(route="generate-upload-url", methods=["POST"])
def generate_upload_url(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generates a write-only SAS URL so the client can upload a .txt file
    directly to Azure Blob Storage without needing Azure credentials.

    Request body:
        { "filename": "mydoc.txt" }

    Response:
        {
            "sas_url": "https://<account>.blob.core.windows.net/uploads/mydoc.txt?<sas>",
            "blob_name": "mydoc.txt",
            "expires_in_minutes": 15
        }
    """
    try:
        req_body = req.get_json()
        if not req_body or "filename" not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'filename' in request body"}),
                status_code=400,
                mimetype="application/json",
            )

        filename = req_body["filename"]
        ALLOWED = (".txt", ".docx")
        if not filename.endswith(ALLOWED):
            return func.HttpResponse(
                json.dumps({"error": "Only .txt and .docx files are supported"}),
                status_code=400,
                mimetype="application/json",
            )

        account_name = os.environ["STORAGE_ACCOUNT_NAME"]
        account_key = os.environ["STORAGE_ACCOUNT_KEY"]
        container_name = "uploads"
        expiry_minutes = 15

        expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=filename,
            account_key=account_key,
            permission=BlobSasPermissions(write=True, create=True),
            expiry=expiry,
        )

        sas_url = (
            f"https://{account_name}.blob.core.windows.net"
            f"/{container_name}/{filename}?{sas_token}"
        )

        logging.info(f"Generated SAS URL for blob: {filename}")

        return func.HttpResponse(
            json.dumps({
                "sas_url": sas_url,
                "blob_name": filename,
                "container": container_name,
                "expires_in_minutes": expiry_minutes,
            }),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.error(f"generate_upload_url error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


# ---------------------------------------------------------------------------
# PATH C — Blob Trigger  (fires automatically when a file lands in uploads/)
# ---------------------------------------------------------------------------
@app.blob_trigger(
    arg_name="blob",
    path="uploads/{name}",
    connection="AzureWebJobsStorage",
    data_type="binary",
)
def process_blob(blob: func.InputStream):
    """
    Automatically triggered when a .txt file is uploaded to the 'uploads' container.
    Reads the file, runs it through the 3-agent pipeline, saves an improved
    .docx document to the 'results' container, and stores debug metadata as JSON.
    """
    blob_name = blob.name  # e.g. "uploads/mydoc.txt"
    filename = blob_name.split("/")[-1]  # e.g. "mydoc.txt"

    logging.info(f"Blob trigger fired for: {blob_name}")
    account_name = os.environ["STORAGE_ACCOUNT_NAME"]
    account_key = os.environ["STORAGE_ACCOUNT_KEY"]
    base_name, _ = os.path.splitext(filename)
    result_blob_name = f"{base_name}.metadata.json"
    improved_docx_blob_name = f"{base_name}_improved.docx"

    try:
        # Skip unsupported file types silently
        ALLOWED = (".txt", ".docx")
        if not filename.endswith(ALLOWED):
            logging.warning(f"Blob {filename} has unsupported type — skipping")
            return

        # Read raw bytes and extract text based on file type
        raw_bytes = blob.read()
        text = _extract_text(raw_bytes, filename)
        logging.info(f"Read {len(text)} characters from blob: {filename}")

        if not text.strip():
            logging.warning(f"Blob {filename} is empty — skipping processing")
            return

        # Run through the agent pipeline
        final_state = _run_agent_pipeline(text)

        result = {
            "success": True,
            "source_blob": blob_name,
            "result_blob": f"results/{improved_docx_blob_name}",
            "metadata_blob": f"results/{result_blob_name}",
            "original_text": final_state.get("text", ""),
            "enhanced_text": final_state.get("enhanced_text", ""),
            "synonyms_found": len(final_state.get("synonyms", {})),
            "parsed_data": final_state.get("parsed_data", {}),
            "workflow_info": {
                "agents_used": ["parse_text", "find_equivalents", "consolidate_text"],
                "workflow_type": "blob_trigger_pipeline",
                "version": "1.2",
            },
        }

        # Save result to the 'results' container
        blob_service = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net",
            credential=account_key,
        )
        results_container = blob_service.get_container_client("results")
        enhanced_text = final_state.get("enhanced_text", "") or final_state.get("text", "")
        improved_docx_bytes = _build_docx_bytes_from_text(enhanced_text)

        results_container.upload_blob(
            name=improved_docx_blob_name,
            data=improved_docx_bytes,
            overwrite=True,
            content_settings=ContentSettings(
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )
        logging.info("Improved DOCX saved to results/%s", improved_docx_blob_name)

        results_container.upload_blob(
            name=result_blob_name,
            data=json.dumps(result, ensure_ascii=False),
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json"),
        )

        logging.info(f"Result saved to results/{result_blob_name}")

    except Exception as e:
        error_payload = {
            "success": False,
            "source_blob": blob_name,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "workflow_info": {
                "workflow_type": "blob_trigger_pipeline",
                "version": "1.1",
            },
        }

        logging.exception("process_blob error for %s", blob_name)

        try:
            blob_service = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=account_key,
            )
            results_container = blob_service.get_container_client("results")
            results_container.upload_blob(
                name=result_blob_name,
                data=json.dumps(error_payload, ensure_ascii=False),
                overwrite=True,
            )
            logging.info("Saved error payload to results/%s", result_blob_name)
        except Exception:
            logging.exception("Failed to persist error payload for %s", blob_name)
