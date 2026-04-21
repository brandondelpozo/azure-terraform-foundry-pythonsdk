#!/usr/bin/env python3
"""
Test script to verify LangGraph pipeline works correctly
Run this before deploying to Azure
"""

import sys
import os
import logging

# Add the function directory to Python path
sys.path.insert(0, '/Users/brandon.del/Public/Globant/Deloitte/azure-terraform-foundry-endpoint-python/function')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_langgraph_pipeline():
    """Test the LangGraph pipeline locally"""
    
    try:
        # Test imports
        print("Testing imports...")
        from agents.langgraph_pipeline import run_langgraph_document_pipeline
        from agents.parse_text_agent import AgentState
        print("✅ Imports successful")
        
        # Test sample text
        sample_text = """AI and the Future of Work
Artificial intelligence is transforming the way organizations operate and make decisions.
Machine learning algorithms can analyze vast amounts of data to identify patterns and generate insights.
Natural language processing enables computers to understand and generate human language with remarkable accuracy.
The integration of AI into business processes has led to significant improvements in efficiency and productivity.
The future of work will require humans and machines to collaborate in ways that maximize the strengths of both."""
        
        print(f"Testing with sample text ({len(sample_text)} characters)...")
        
        # Run pipeline
        result = run_langgraph_document_pipeline(sample_text, "test.docx")
        
        print("✅ Pipeline executed successfully")
        print(f"Original text length: {len(result.get('text', ''))}")
        print(f"Enhanced text length: {len(result.get('enhanced_text', ''))}")
        print(f"Synonyms found: {len(result.get('synonyms', {}))}")
        print(f"Synonyms: {result.get('synonyms', {})}")
        
        # Check if text was enhanced
        if result.get('enhanced_text') != result.get('text'):
            print("✅ Text was enhanced (different from original)")
        else:
            print("⚠️  Text was NOT enhanced (same as original)")
            
        if result.get('synonyms'):
            print("✅ Synonyms were found")
        else:
            print("⚠️  No synonyms found - check Azure OpenAI connection")
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing LangGraph Pipeline...")
    print("=" * 50)
    
    success = test_langgraph_pipeline()
    
    print("=" * 50)
    if success:
        print("✅ All tests passed! Ready for deployment.")
    else:
        print("❌ Tests failed! Fix issues before deploying.")
    
    sys.exit(0 if success else 1)