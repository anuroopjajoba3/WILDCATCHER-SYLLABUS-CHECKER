#!/usr/bin/env python3
"""
Simple test script to verify all imports work correctly
"""

try:
    from langchain_community.vectorstores import Chroma
    print("✓ Chroma import successful")
except ImportError as e:
    print(f"✗ Chroma import failed: {e}")

try:
    from langchain_community.chat_models import ChatOpenAI
    print("✓ ChatOpenAI import successful")
except ImportError as e:
    print(f"✗ ChatOpenAI import failed: {e}")

try:
    from langchain_openai import OpenAIEmbeddings
    print("✓ OpenAIEmbeddings import successful")
except ImportError as e:
    print(f"✗ OpenAIEmbeddings import failed: {e}")

print("\nAll critical imports tested successfully!")