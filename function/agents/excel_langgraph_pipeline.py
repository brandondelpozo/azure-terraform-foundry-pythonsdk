import logging
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# Import Excel-specific agents
from .parse_excel_agent import parse_excel_agent, ExcelAgentState
from .analyze_excel_agent import analyze_excel_agent

def run_excel_langgraph_pipeline(excel_content: bytes, filename: str = "unknown.xlsx") -> Dict[str, Any]:
    """
    Run the Excel processing pipeline using LangGraph
    
    Args:
        excel_content: Raw bytes of the Excel file
        filename: Name of the Excel file
        
    Returns:
        Dictionary containing the complete analysis results
    """
    
    logging.info(f"Starting Excel LangGraph pipeline for: {filename}")
    
    try:
        # Initialize the state
        initial_state = ExcelAgentState(
            text="",
            parsed_data={},
            synonyms={},
            title="",
            summary="",
            enhanced_text="",
            pdf_content="",
            token_usage={},
            excel_content=excel_content,
            filename=filename
        )
        
        # Create the LangGraph workflow
        workflow = create_excel_workflow()
        
        # Execute the workflow
        result = workflow.invoke(initial_state)
        
        # Prepare final response - simplified like word files
        final_result = {
            "success": True,
            "filename": filename,
            "title": result.get("title", ""),
            "summary": result.get("summary", ""),
            "parsed_data": result.get("parsed_data", {}),
            "token_usage": result.get("token_usage", {}),
            "workflow_info": {
                "agents_used": ["parse_excel", "analyze_excel"],
                "workflow_type": "excel_langgraph_pipeline",
                "version": "1.0",
                "langgraph_enabled": True,
                "azure_openai_enabled": True,
                "processing_timestamp": _get_timestamp()
            }
        }
        
        logging.info(f"Excel LangGraph pipeline completed successfully for: {filename}")
        return final_result
        
    except Exception as e:
        logging.error(f"Excel LangGraph pipeline failed for {filename}: {str(e)}")
        return {
            "success": False,
            "filename": filename,
            "error": str(e),
            "title": "Excel Processing - Error",
            "summary": f"Failed to process Excel file: {str(e)}",
            "parsed_data": {"error": str(e)},
            "token_usage": {},
            "workflow_info": {
                "agents_used": ["parse_excel", "analyze_excel"],
                "workflow_type": "excel_langgraph_pipeline",
                "version": "1.0",
                "langgraph_enabled": True,
                "azure_openai_enabled": True,
                "error_timestamp": _get_timestamp()
            }
        }

def create_excel_workflow() -> StateGraph:
    """Create the Excel processing workflow using LangGraph"""
    
    # Define the workflow
    workflow = StateGraph(ExcelAgentState)
    
    # Add nodes (agents)
    workflow.add_node("parse_excel", parse_excel_agent)
    workflow.add_node("analyze_excel", analyze_excel_agent)
    
    # Define the flow
    workflow.set_entry_point("parse_excel")
    workflow.add_edge("parse_excel", "analyze_excel")
    workflow.add_edge("analyze_excel", END)
    
    # Compile the workflow
    return workflow.compile()

def _get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

# Alternative function for backward compatibility
def run_langgraph_excel_pipeline(excel_content: bytes, filename: str = "unknown.xlsx") -> Dict[str, Any]:
    """Alias for run_excel_langgraph_pipeline for consistency with existing naming"""
    return run_excel_langgraph_pipeline(excel_content, filename)