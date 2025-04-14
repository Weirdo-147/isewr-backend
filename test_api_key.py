"""
Direct test for Gemini API key using the hardcoded value
"""
import requests
import json

# Hardcoded API key for testing
API_KEY = 'AIzaSyDQjnloLAbT3vOwl2EXFvKEyNOqA1NLsbo'

def test_api_key():
    """Test if the API key is valid using direct API call"""
    print(f"Testing API key: {API_KEY}")
    
    # Test with a simple text generation request to check if the key is valid
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    
    try:
        # Make a direct HTTP request to list models
        response = requests.get(url)
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            
            print(f"Successfully retrieved {len(models)} models:")
            for model in models[:5]:  # Print first 5 models
                print(f"- {model.get('name')}")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
        
    except Exception as e:
        print(f"Error testing API key: {e}")
        return False

if __name__ == "__main__":
    success = test_api_key()
    if success:
        print("✅ API key is valid!")
    else:
        print("❌ API key is invalid or has insufficient permissions!") 