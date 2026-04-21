from langgraph.graph import StateGraph, START, END
from typing import TypedDict
import logging

from .parse_text_agent import parse_text_agent, AgentState
from .find_equivalents_agent import find_equivalents_agent
from .consolidate_text_agent import consolidate_text_agent

def create_document_processing_graph():
    """Create LangGraph StateGraph for document processing"""
    
    # Create the graph with AgentState
    graph = StateGraph(AgentState)
    
    # Add the 3 existing agents as nodes
    graph.add_node("parse_text", parse_text_agent)
    graph.add_node("find_equivalents", find_equivalents_agent)  # Will use Azure OpenAI Completions
    graph.add_node("consolidate_text", consolidate_text_agent)
    
    # Define sequential flow: parse → find → consolidate
    graph.add_edge(START, "parse_text")
    graph.add_edge("parse_text", "find_equivalents")
    graph.add_edge("find_equivalents", "consolidate_text")
    graph.add_edge("consolidate_text", END)
    
    # Compile the graph
    compiled_graph = graph.compile()
    
    logging.info("LangGraph document processing pipeline created")
    return compiled_graph

def run_langgraph_document_pipeline(text: str, filename: str = "document.docx") -> dict:
    """Execute the LangGraph pipeline for document processing"""
    
    # Initialize state
    initial_state = {
        "text": text,
        "parsed_data": {},
        "synonyms": {},
        "enhanced_text": "",
        "pdf_content": "",
        "token_usage": {},  # Add token_usage to initial state
    }
    
    # Create and invoke the graph
    app = create_document_processing_graph()
    
    logging.info(f"Starting LangGraph pipeline for: {filename}")
    final_state = app.invoke(initial_state)
    
    logging.info(f"LangGraph pipeline completed for: {filename}")
    logging.info(f"Final state keys: {list(final_state.keys())}")
    logging.info(f"Final state token_usage: {final_state.get('token_usage', 'MISSING')}")
    logging.info(f"Final state token_usage type: {type(final_state.get('token_usage'))}")
    logging.info(f"Final state token_usage value: {repr(final_state.get('token_usage'))}")
    return final_state