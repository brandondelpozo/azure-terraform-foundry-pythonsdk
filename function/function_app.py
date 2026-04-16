import azure.functions as func
import azure.durable_functions as df
import json
import logging
from typing import Dict, Any
from agents.parse_text_agent import parse_text_agent, AgentState
from agents.find_equivalents_agent import find_equivalents_agent
from agents.consolidate_text_agent import consolidate_text_agent

# Configure logging
logging.basicConfig(level=logging.INFO)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# HTTP Trigger - Entry Point
@app.route(route="process-text", methods=["POST"])
def http_start(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger that processes text (synchronous response)."""
    try:
        req_body = req.get_json()
        if not req_body or 'text' not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'text' in request body"}),
                status_code=400,
                mimetype="application/json"
            )

        text = req_body.get('text')
        logging.info(f'Processing text from /process-text: {text[:100]}...')

        # Create initial state
        initial_state = {
            "text": text,
            "parsed_data": {},
            "synonyms": {},
            "enhanced_text": "",
            "pdf_content": ""
        }

        # Execute agents directly for immediate response
        state_after_parse = parse_text_agent(initial_state)
        state_after_equivalents = find_equivalents_agent(state_after_parse)
        final_state = consolidate_text_agent(state_after_equivalents)

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
                "version": "2.1"
            }
        }

        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"HTTP trigger error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

# Orchestrator Function - Contains LangGraph Workflow
@app.orchestration_trigger(context_name="context")
def text_processing_orchestrator(context: df.DurableOrchestrationContext):
    """Orchestrator function that manages the LangGraph workflow"""
    try:
        input_data = context.get_input()
        text = input_data.get('text', '')
        
        logging.info(f"Orchestrator started for text: {text[:50]}...")
        
        # Create initial state
        initial_state = {
            "text": text,
            "parsed_data": {},
            "synonyms": {},
            "enhanced_text": "",
            "pdf_content": ""
        }
        
        # Execute workflow steps using durable activities
        # Step 1: Parse Text
        state_after_parse = yield context.call_activity("parse_text_activity", initial_state)
        
        # Step 2: Find Equivalents
        state_after_equivalents = yield context.call_activity("find_equivalents_activity", state_after_parse)
        
        # Step 3: Consolidate Text
        final_state = yield context.call_activity("consolidate_text_activity", state_after_equivalents)
        
        # Format final response
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
                "instance_id": context.instance_id
            }
        }
        
        logging.info(f"Orchestration completed successfully for instance: {context.instance_id}")
        return response
        
    except Exception as e:
        logging.error(f"Orchestrator error: {str(e)}")
        return {"error": str(e), "workflow": "durable_langgraph_hybrid"}

# Activity Functions - Wrap your existing agents
@app.activity_trigger(input_name="input")
def parse_text_activity(input: dict) -> dict:
    """Activity function for parse text agent"""
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
    """Activity function for find equivalents agent"""
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
    """Activity function for consolidate text agent"""
    logging.info("Executing consolidate_text_activity")
    try:
        result = consolidate_text_agent(input)
        logging.info("consolidate_text_activity completed successfully")
        return result
    except Exception as e:
        logging.error(f"consolidate_text_activity error: {str(e)}")
        raise

# Legacy endpoint for backward compatibility (DISABLED)
# @app.route(route="ask", methods=["POST"])
# def ask_legacy(req: func.HttpRequest) -> func.HttpResponse:
#     """Legacy endpoint - converts message to text format"""
#     try:
#         req_body = req.get_json()
#         if req_body and 'message' in req_body:
#             # Convert to new format and redirect to durable orchestration
#             new_body = {'text': req_body['message']}
#
#             client = df.DurableOrchestrationClient(req)
#             instance_id = client.start_new("text_processing_orchestrator", None, new_body)
#
#             logging.info(f"Started legacy orchestration with instance ID: {instance_id}")
#
#             return client.create_check_status_response(req, instance_id)
#         else:
#             return func.HttpResponse(
#                 json.dumps({"error": "Missing 'message' in request body"}),
#                 status_code=400,
#                 mimetype="application/json"
#             )
#     except Exception as e:
#         logging.error(f"Legacy endpoint error: {str(e)}")
#         return func.HttpResponse(
#             json.dumps({"error": str(e)}),
#             status_code=500,
#             mimetype="application/json"
#         )

'''
# Direct endpoint for immediate response (fallback)
@app.route(route="process-text-sync", methods=["POST"])
def process_text_sync(req: func.HttpRequest) -> func.HttpResponse:
    """Synchronous endpoint for immediate response (fallback)"""
    try:
        req_body = req.get_json()
        if not req_body or 'text' not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'text' in request body"}),
                status_code=400,
                mimetype="application/json"
            )
        
        text = req_body.get('text')
        logging.info(f'Processing text synchronously: {text[:100]}...')
        
        # Create initial state
        initial_state = {
            "text": text,
            "parsed_data": {},
            "synonyms": {},
            "enhanced_text": "",
            "pdf_content": ""
        }
        
        # Execute agents directly (original workflow)
        state_after_parse = parse_text_agent(initial_state)
        state_after_equivalents = find_equivalents_agent(state_after_parse)
        final_state = consolidate_text_agent(state_after_equivalents)
        
        # Create response
        response = {
            "success": True,
            "original_text": final_state.get("text", ""),
            "enhanced_text": final_state.get("enhanced_text", ""),
            "synonyms_found": len(final_state.get("synonyms", {})),
            "pdf_base64": final_state.get("pdf_content", ""),
            "parsed_data": final_state.get("parsed_data", {}),
            "workflow_info": {
                "agents_used": ["parse_text", "find_equivalents", "consolidate_text"],
                "workflow_type": "synchronous_fallback",
                "version": "2.0"
            }
        }
        
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Sync function execution error: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "details": str(e),
                "workflow": "synchronous_fallback"
            }),
            status_code=500,
            mimetype="application/json"
        )
'''