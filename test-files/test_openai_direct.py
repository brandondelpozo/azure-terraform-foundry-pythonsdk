import requests
import json
import os

# Test Azure OpenAI Chat Completions API directly
def test_azure_openai():
    openai_endpoint = "https://australiaeast.api.cognitive.microsoft.com/"
    openai_api_key = "fd733a73b8994c61a2f08e0081709d85"
    openai_model = "gpt-5.4-nano"
    
    chat_completions_url = f"{openai_endpoint}openai/deployments/{openai_model}/chat/completions?api-version=2025-04-01-preview"
    
    headers = {
        "Content-Type": "application/json",
        "api-key": openai_api_key
    }
    
    messages = [
        {
            "role": "system",
            "content": "You are a professional writing assistant that finds synonyms for business documents. Return only valid JSON format."
        },
        {
            "role": "user", 
            "content": """Analyze this document text and find professional synonyms for important words.

Document Text: "This comprehensive analysis provides strategic insights."

Instructions:
- Find nouns, verbs, and adjectives that can be enhanced
- Skip common words (the, and, is, a, an, to, for, etc.)
- Provide 3 professional synonyms for each word
- Return only valid JSON format
- Focus on business/professional context

Example JSON format:
{"analyze": ["examine", "evaluate", "assess"], "important": ["crucial", "vital", "significant"]}

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
        print("Calling Azure OpenAI Chat Completions API...")
        response = requests.post(chat_completions_url, headers=headers, json=payload, timeout=60)
        
        print(f"Response status: {response.status_code}")
        result = response.json()
        
        print(f"Full response: {json.dumps(result, indent=2)}")
        
        if "usage" in result:
            print(f"Token usage: {result['usage']}")
        
        if "choices" in result and len(result["choices"]) > 0:
            completion_text = result["choices"][0]["message"]["content"].strip()
            print(f"Completion text: {completion_text}")
            
            try:
                synonyms = json.loads(completion_text)
                print(f"Parsed synonyms: {synonyms}")
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed: {e}")
                print(f"Raw text: {repr(completion_text)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_azure_openai()