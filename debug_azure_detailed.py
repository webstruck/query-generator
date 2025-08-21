#!/usr/bin/env python3
"""
Detailed Azure debugging script to diagnose empty response issues.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import openai

# Load .env file
load_dotenv()

def test_direct_azure_client():
    """Test Azure client directly with detailed debugging."""
    print("=== Direct Azure Client Test ===")
    
    # Get environment variables
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") 
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    
    print(f"API Key: {api_key[:10]}...{api_key[-4:] if api_key else 'MISSING'}")
    print(f"Endpoint: {endpoint}")
    print(f"Deployment: {deployment}")
    print(f"API Version: {api_version}")
    
    if not all([api_key, endpoint, deployment]):
        print("❌ Missing required environment variables")
        return
    
    try:
        # Create Azure client directly
        client = openai.AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
        print("✅ Azure client created")
        
        # Test with very simple parameters
        print("\n--- Testing with minimal parameters ---")
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        print(f"Response object: {type(response)}")
        print(f"Response choices: {len(response.choices) if response.choices else 0}")
        
        if response.choices:
            content = response.choices[0].message.content
            print(f"Content: '{content}'")
            print(f"Content type: {type(content)}")
            print(f"Content length: {len(content) if content else 0}")
            
            if content:
                print("✅ Got response content!")
            else:
                print("❌ Content is None or empty")
                
                # Debug response structure
                print(f"Full choice: {response.choices[0]}")
                print(f"Message: {response.choices[0].message}")
        else:
            print("❌ No choices in response")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e)}")
        
        # More specific error handling
        if "401" in str(e):
            print("💡 Authentication error - check your API key")
        elif "404" in str(e):
            print("💡 Not found - check your endpoint URL and deployment name")
        elif "quota" in str(e).lower():
            print("💡 Quota exceeded - check your Azure OpenAI usage limits")

def test_different_parameters():
    """Test with different parameter combinations."""
    print("\n=== Testing Different Parameters ===")
    
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    if not all([api_key, endpoint, deployment]):
        print("❌ Skipping - missing environment variables")
        return
        
    client = openai.AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version="2024-02-01"
    )
    
    test_params = [
        {"max_tokens": 10, "temperature": 0},
        {"max_tokens": 50, "temperature": 0.5},
        {"max_tokens": 20, "temperature": 1.0},
    ]
    
    for i, params in enumerate(test_params, 1):
        try:
            print(f"\nTest {i}: {params}")
            response = client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": "Say hello"}],
                **params
            )
            
            content = response.choices[0].message.content if response.choices else None
            print(f"   Result: '{content}'")
            
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    print("🔍 Detailed Azure OpenAI Debugging")
    print("=" * 50)
    
    test_direct_azure_client()
    test_different_parameters()
    
    print("\n" + "=" * 50)
    print("🏁 Debug completed!")