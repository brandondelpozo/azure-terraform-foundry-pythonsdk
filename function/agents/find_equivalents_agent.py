import logging
import requests
import os
from .parse_text_agent import AgentState

def find_equivalents_agent(state: AgentState) -> AgentState:
    """Find synonyms and equivalents for text enhancement"""
    text = state.get("text", "")
    
    # Simple synonym mapping for demo
    synonym_map = {
        "good": ["excellent", "great", "outstanding"],
        "bad": ["poor", "terrible", "awful"],
        "big": ["large", "huge", "enormous"],
        "small": ["tiny", "little", "minute"],
        "happy": ["joyful", "delighted", "pleased"],
        "sad": ["sorrowful", "melancholy", "dejected"]
    }
    
    words = text.lower().split()
    found_synonyms = {}
    
    for word in words:
        clean_word = word.strip('.,!?;:"')
        if clean_word in synonym_map:
            found_synonyms[clean_word] = synonym_map[clean_word]
    
    state["synonyms"] = found_synonyms
    logging.info(f"Found synonyms for {len(found_synonyms)} words")
    
    return state