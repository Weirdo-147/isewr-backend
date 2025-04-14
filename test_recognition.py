"""
Test script to verify that image recognition works with Gemini
"""
import os
import requests
import base64
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def test_image_recognition(image_url="https://picsum.photos/200"):
    """Test image recognition with Gemini"""
    print(f"Testing image recognition with URL: {image_url}")
    
    # Get API key
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("ERROR: No API key found in environment variables")
        return False
    
    try:
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Download the image
        response = requests.get(image_url)
        if response.status_code != 200:
            print(f"ERROR: Failed to download image, status code: {response.status_code}")
            return False
        
        # Get image content
        image_content = response.content
        
        # Load Gemini Vision model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare the image
        image_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_content).decode('utf-8')
            }
        ]
        
        # Generate scene description
        prompt = "Describe this image in detail with one paragraph."
        response = model.generate_content([prompt, image_parts[0]])
        scene_description = response.text.strip()
        
        print("\nGENERATED DESCRIPTION:")
        print(scene_description)
        
        # Detect objects
        objects_prompt = "List all objects visible in this image, one per line."
        objects_response = model.generate_content([objects_prompt, image_parts[0]])
        objects_text = objects_response.text.strip()
        
        print("\nDETECTED OBJECTS:")
        print(objects_text)
        
        return True
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_image_recognition()
    if success:
        print("\n✅ Image recognition test completed successfully!")
    else:
        print("\n❌ Image recognition test failed!") 