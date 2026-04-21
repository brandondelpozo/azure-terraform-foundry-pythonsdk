import logging
import requests
import os
import json
from .parse_text_agent import AgentState

def _call_azure_openai_chat_completions_for_synonyms(text: str) -> tuple[dict, dict]:
    """Call Azure OpenAI Chat Completions API for synonym finding
    
    Returns:
        tuple: (synonyms_dict, token_usage_dict)
    """
    
    openai_endpoint = os.environ.get("OPENAI_ENDPOINT")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-5.4-nano")
    
    if not openai_endpoint or not openai_api_key:
        logging.warning("Azure OpenAI credentials not found, using fallback synonyms")
        return {}, {}
    
    # Azure OpenAI Chat Completions endpoint
    chat_completions_url = f"{openai_endpoint}openai/deployments/{openai_model}/chat/completions?api-version=2025-04-01-preview"
    
    headers = {
        "Content-Type": "application/json",
        "api-key": openai_api_key
    }
    
    # Create chat completion messages
    messages = [
        {
            "role": "system",
            "content": "You are a professional writing assistant that finds synonyms for business documents. Return only valid JSON format."
        },
        {
            "role": "user", 
            "content": f"""Analyze this document text and find professional synonyms for important words.

Document Text: "{text}"

Instructions:
- Find nouns, verbs, and adjectives that can be enhanced
- Skip common words (the, and, is, a, an, to, for, etc.)
- Provide 3 professional synonyms for each word
- Return only valid JSON format
- Focus on business/professional context

Example JSON format:
{{"analyze": ["examine", "evaluate", "assess"], "important": ["crucial", "vital", "significant"]}}

JSON Response:"""
        }
    ]

    payload = {
        "messages": messages,
        "max_completion_tokens": 800,
        "temperature": 0.2,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0
    }
    
    try:
        logging.info("Calling Azure OpenAI Chat Completions API for synonym analysis...")
        response = requests.post(chat_completions_url, headers=headers, json=payload, timeout=60)
        
        logging.info(f"Azure OpenAI Chat Completions response status: {response.status_code}")
        response.raise_for_status()
        
        result = response.json()
        
        # Extract token usage information
        token_usage = {}
        if "usage" in result:
            token_usage = {
                "prompt_tokens": result["usage"].get("prompt_tokens", 0),
                "completion_tokens": result["usage"].get("completion_tokens", 0),
                "total_tokens": result["usage"].get("total_tokens", 0)
            }
            logging.info(f"Token usage - Prompt: {token_usage['prompt_tokens']}, Completion: {token_usage['completion_tokens']}, Total: {token_usage['total_tokens']}")
        
        # Extract completion text from chat response
        if "choices" in result and len(result["choices"]) > 0:
            completion_text = result["choices"][0]["message"]["content"].strip()
            logging.info(f"Azure OpenAI chat completion: {completion_text[:200]}...")
            
            # Try to parse as JSON
            try:
                synonyms = json.loads(completion_text)
                
                # Validate it's a dictionary
                if isinstance(synonyms, dict) and synonyms:
                    logging.info(f"Azure OpenAI Chat Completions found synonyms for {len(synonyms)} words")
                    return synonyms, token_usage
                else:
                    logging.warning("Azure OpenAI returned empty or invalid dictionary")
                    return {}, token_usage
                    
            except json.JSONDecodeError as json_err:
                logging.error(f"Failed to parse Azure OpenAI completion as JSON: {json_err}")
                logging.error(f"Raw completion text: {completion_text}")
                return {}, token_usage
        else:
            logging.error("Azure OpenAI response missing choices")
            return {}, token_usage
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Azure OpenAI Chat Completions API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response content: {e.response.text}")
        return {}, {}
    except KeyError as e:
        logging.error(f"Unexpected Azure OpenAI response structure: {str(e)}")
        logging.error(f"Full response: {result}")
        return {}, {}
    except Exception as e:
        logging.error(f"Unexpected error calling Azure OpenAI Chat Completions: {str(e)}")
        return {}, {}

def find_equivalents_agent(state: AgentState) -> AgentState:
    """LangGraph node: Find synonyms using Azure OpenAI Completions with fallback"""
    text = state.get("text", "")
    
    logging.info("Starting synonym analysis with Azure OpenAI Chat Completions...")
    
    # Try Azure OpenAI Chat Completions first
    ai_synonyms, token_usage = _call_azure_openai_chat_completions_for_synonyms(text)
    
    if ai_synonyms:
        # Use AI-generated synonyms
        state["synonyms"] = ai_synonyms
        state["token_usage"] = token_usage
        logging.info(f"Using Azure OpenAI Chat Completions synonyms for {len(ai_synonyms)} words")
    else:
        # Fallback to enhanced hardcoded synonyms
        logging.info("Using enhanced fallback synonym mapping")
        
        professional_synonym_map = {
            # Business terms
            "analyze": ["examine", "evaluate", "assess"],
            "important": ["crucial", "vital", "significant"],
            "document": ["report", "manuscript", "file"],
            "process": ["procedure", "method", "workflow"],
            "review": ["examine", "evaluate", "inspect"],
            "implement": ["execute", "deploy", "establish"],
            "manage": ["oversee", "coordinate", "supervise"],
            "develop": ["create", "establish", "formulate"],
            "improve": ["enhance", "optimize", "refine"],
            "effective": ["efficient", "successful", "productive"],
            
            # Quality terms
            "good": ["excellent", "superior", "outstanding"],
            "bad": ["poor", "inadequate", "substandard"],
            "big": ["substantial", "significant", "considerable"],
            "small": ["minimal", "limited", "modest"],
            "fast": ["rapid", "swift", "expeditious"],
            "slow": ["gradual", "deliberate", "measured"],
            
            # Action terms
            "show": ["demonstrate", "illustrate", "exhibit"],
            "use": ["utilize", "employ", "apply"],
            "make": ["create", "produce", "generate"],
            "get": ["obtain", "acquire", "secure"],
            "help": ["assist", "support", "facilitate"],
            "work": ["function", "operate", "perform"],
            "find": ["locate", "identify", "discover"],
            "think": ["consider", "contemplate", "analyze"]
        }
        
        # Find synonyms in text
        words = text.lower().split()
        found_synonyms = {}
        
        for word in words:
            # Clean word of punctuation
            clean_word = word.strip('.,!?;:"\'-()[]{}')
            if clean_word in professional_synonym_map:
                found_synonyms[clean_word] = professional_synonym_map[clean_word]
        
        state["synonyms"] = found_synonyms
        state["token_usage"] = {}  # No tokens used for fallback
        logging.info(f"Fallback found synonyms for {len(found_synonyms)} words")
    
    logging.info("Synonym analysis completed")
    return state