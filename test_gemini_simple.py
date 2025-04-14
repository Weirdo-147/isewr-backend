"""
Simple test for Gemini API key
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def test_gemini_api_key():
    """Test if the Gemini API key is valid"""
    print("Testing Gemini API key...")
    
    # Get API key from environment
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Error: GOOGLE_API_KEY not set in environment variables")
        return False
    
    print(f"Full API key for debugging: {api_key}")
    print(f"API key found: {api_key[:5]}...{api_key[-5:]}")
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # List available models - this is a simple API call that validates the key
        models = genai.list_models()
        
        print(f"Successfully retrieved {len(models)} models:")
        for model in models[:5]:  # Print first 5 models
            print(f"- {model.name}")
        
        return True
    except Exception as e:
        print(f"Error testing Gemini API key: {e}")
        return False

if __name__ == "__main__":
    success = test_gemini_api_key()
    if success:
        print("✅ Gemini API key is valid!")
    else:
        print("❌ Gemini API key is invalid or has insufficient permissions!") 