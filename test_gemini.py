"""
Test Google Gemini API connection
"""
import os
import base64
import requests
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test basic Gemini image captioning"""
    print("Testing Google Gemini API...")
    
    # Check for API key
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Error: GOOGLE_API_KEY not set in environment variables")
        return False
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Download a sample image
        image_url = "https://picsum.photos/200"
        response = requests.get(image_url)
        if response.status_code != 200:
            print(f"Error downloading test image: HTTP {response.status_code}")
            return False
        
        image_bytes = response.content
        
        # Create a Gemini model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare the image
        image_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode('utf-8')
            }
        ]
        
        # Generate a caption
        prompt = "Describe what's in this image in a single sentence."
        response = model.generate_content([prompt, image_parts[0]])
        
        print(f"Gemini response: {response.text}")
        return True
    
    except Exception as e:
        print(f"Error testing Gemini API: {e}")
        return False

if __name__ == "__main__":
    success = test_gemini_api()
    if success:
        print("✅ Gemini API test successful!")
    else:
        print("❌ Gemini API test failed!") 