import logging
from typing import TypedDict, Dict, Any
import json

class ExcelAgentState(TypedDict):
    text: str
    parsed_data: dict
    synonyms: dict
    title: str
    summary: str
    enhanced_text: str
    pdf_content: str
    token_usage: dict
    excel_content: bytes
    filename: str

def analyze_excel_agent(state: ExcelAgentState) -> ExcelAgentState:
    """Analyze Excel content and generate title and summary using Azure OpenAI"""
    
    try:
        # Import Azure OpenAI client
        from azure.openai import OpenAIClient
        from azure.core.credentials import AzureKeyCredential
        
        # Get configuration from environment
        openai_endpoint = os.environ.get("OPENAI_ENDPOINT")
        openai_key = os.environ.get("OPENAI_KEY")
        model_deployment = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-5.4-nano")
        
        if not openai_endpoint or not openai_key:
            logging.error("Missing OpenAI configuration")
            state["title"] = "Excel Analysis - Configuration Error"
            state["summary"] = "Unable to analyze Excel file due to missing OpenAI configuration."
            return state
        
        # Initialize OpenAI client
        client = OpenAIClient(
            endpoint=openai_endpoint,
            credential=AzureKeyCredential(openai_key)
        )
        
        # Get parsed data and text
        parsed_data = state.get("parsed_data", {})
        text = state.get("text", "")
        filename = state.get("filename", "unknown.xlsx")
        
        # Create analysis prompt
        analysis_prompt = _create_analysis_prompt(parsed_data, text, filename)
        
        # Call OpenAI for analysis
        response = client.chat.completions.create(
            model=model_deployment,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional document analyst that creates concise titles and summaries for Excel files. Return only valid JSON format."
                },
                {
                    "role": "user", 
                    "content": analysis_prompt
                }
            ],
            max_tokens=300,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        analysis_result = json.loads(response_text)
        
        # Update state with analysis results - simplified like word files
        state["title"] = analysis_result.get("title", "Excel Analysis")
        state["summary"] = analysis_result.get("summary", "Excel file processed successfully")
        
        # Track token usage
        if hasattr(response, 'usage'):
            state["token_usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        logging.info(f"Successfully analyzed Excel file '{filename}': {state['title']}")
        
    except Exception as e:
        logging.error(f"Error analyzing Excel file: {str(e)}")
        state["title"] = "Excel Analysis - Error"
        state["summary"] = f"Unable to analyze Excel file due to error: {str(e)}"
    
    return state

def _create_analysis_prompt(parsed_data: Dict[str, Any], text: str, filename: str) -> str:
    """Create a comprehensive analysis prompt for OpenAI"""
    
    # Extract key information from parsed data
    file_info = {
        "filename": filename,
        "total_sheets": parsed_data.get("total_sheets", 0),
        "sheet_names": parsed_data.get("sheet_names", []),
        "total_rows": parsed_data.get("total_rows", 0),
        "total_columns": parsed_data.get("total_columns", 0),
        "total_cells": parsed_data.get("total_cells", 0),
        "complexity": parsed_data.get("file_analysis", {}).get("complexity", "Unknown"),
        "data_categories": parsed_data.get("file_analysis", {}).get("data_categories", []),
        "structure_type": parsed_data.get("file_analysis", {}).get("structure_type", "Unknown")
    }
    
    # Get sheet details
    sheets_info = []
    for sheet_name, sheet_data in parsed_data.get("sheets", {}).items():
        if "error" not in sheet_data:
            sheets_info.append({
                "name": sheet_name,
                "rows": sheet_data.get("rows", 0),
                "columns": sheet_data.get("columns", 0),
                "has_headers": sheet_data.get("has_headers", False),
                "data_types": sheet_data.get("data_types", {})
            })
    
    # Truncate text if too long
    max_text_length = 2000
    truncated_text = text[:max_text_length] + "..." if len(text) > max_text_length else text
    
    prompt = f"""Analyze this Excel file content and create a professional title and summary.

Excel Content: "{truncated_text}"

File Information:
- Filename: {file_info['filename']}
- Sheets: {file_info['total_sheets']} ({', '.join(file_info['sheet_names'])})
- Size: {file_info['total_rows']} rows × {file_info['total_columns']} columns

Instructions:
- Create a title that captures the essence of the Excel file (5-10 words maximum)
- Create a summary that highlights the main points (2-3 sentences)
- Focus on business/professional context
- Return only valid JSON format

Example JSON format:
{{"title": "Excel File Title Here", "summary": "Excel file summary in 2-3 sentences highlighting the main points and key information."}}

JSON Response:"""
    
    return prompt

# Import os for environment variables
import os