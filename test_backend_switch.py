#!/usr/bin/env python3
"""
Test script to verify backend switching works correctly
"""
import os
from dotenv import load_dotenv
load_dotenv()

def test_backend(backend_name):
    """Test a specific backend configuration"""
    print(f"\n=== Testing {backend_name.upper()} Backend ===")
    
    try:
        # Set environment variable
        os.environ["LLM_BACKEND"] = backend_name
        
        # Import and initialize
        from backend_switch import get_backend
        models = get_backend()
        
        print(f"✅ Backend initialized: {models.name}")
        print(f"✅ LLM type: {type(models.llm).__name__}")
        print(f"✅ Embeddings type: {type(models.embeddings).__name__}")
        
        # Test LLM
        response = models.llm.invoke("Say hello in one word")
        print(f"✅ LLM response: {response.content}")
        
        # Test embeddings
        test_embedding = models.embeddings.embed_query("test")
        print(f"✅ Embedding dimension: {len(test_embedding)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Test all available backends"""
    backends_to_test = ["openai"]
    
    # Only test OSS if Ollama is running
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            backends_to_test.append("oss")
    except:
        print("⚠️  Ollama not running, skipping OSS backend test")
    
    results = {}
    for backend in backends_to_test:
        results[backend] = test_backend(backend)
    
    print("\n=== Test Results ===")
    for backend, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{backend}: {status}")

if __name__ == "__main__":
    main()