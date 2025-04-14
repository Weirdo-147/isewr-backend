"""
Complete test for Google Gemini API with image processing
"""
import os
import base64
import requests
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test Gemini API with text and image processing"""
    print("Testing Google Gemini API...")
    
    # Get API key from environment
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Error: GOOGLE_API_KEY not set in environment variables")
        return False
    
    print(f"API key: {api_key[:5]}...{api_key[-5:]}")
    
    try:
        # 1. First test: List available models
        print("\n=== Step 1: Checking available models ===")
        genai.configure(api_key=api_key)
        models = list(genai.list_models())
        
        print(f"Available models: {len(models)}")
        found_1_5_model = False
        for model in models:
            if "gemini-1.5" in model.name:
                found_1_5_model = True
                print(f"Found Gemini 1.5 model: {model.name}")
        
        if not found_1_5_model:
            print("Warning: No Gemini 1.5 models found")
            print("Available models:")
            for model in models[:5]:
                print(f"- {model.name}")
        
        # 2. Second test: Text generation
        print("\n=== Step 2: Testing text generation ===")
        
        text_model = genai.GenerativeModel('gemini-1.5-pro')
        text_prompt = "What are the main features of Python programming language? Answer in a short paragraph."
        
        text_response = text_model.generate_content(text_prompt)
        print(f"Text generation successful: {text_response.text[:100]}...")
        
        # 3. Third test: Download a sample image
        print("\n=== Step 3: Testing image download ===")
        image_url = "https://picsum.photos/200"
        image_response = requests.get(image_url)
        
        if image_response.status_code != 200:
            print(f"Error downloading image: HTTP {image_response.status_code}")
            return False
        
        image_data = image_response.content
        print(f"Image downloaded successfully: {len(image_data)} bytes")
        
        # 4. Fourth test: Image processing with Gemini
        print("\n=== Step 4: Testing image processing ===")
        
        # Find a model that supports vision
        vision_model_name = 'gemini-1.5-flash'
        vision_model = genai.GenerativeModel(vision_model_name)
        
        # Prepare the image data
        image_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_data).decode('utf-8')
            }
        ]
        
        # Generate image caption
        vision_prompt = "Describe this image in a brief sentence."
        
        try:
            vision_response = vision_model.generate_content([vision_prompt, image_parts[0]])
            print(f"Image caption generated successfully: {vision_response.text}")
        except Exception as img_error:
            print(f"Error in image processing: {img_error}")
            # Try with a different model if available
            if found_1_5_model:
                print("Trying with another Gemini 1.5 model...")
                # Find another 1.5 model
                for model in models:
                    if "gemini-1.5" in model.name and model.name != vision_model_name:
                        alt_model_name = model.name
                        print(f"Trying with alternative model: {alt_model_name}")
                        try:
                            alt_model = genai.GenerativeModel(alt_model_name)
                            alt_response = alt_model.generate_content([vision_prompt, image_parts[0]])
                            print(f"Alternative model succeeded: {alt_response.text}")
                            return True
                        except Exception as alt_error:
                            print(f"Alternative model also failed: {alt_error}")
            return False
        
        return True
    
    except Exception as e:
        print(f"Error testing Gemini API: {e}")
        return False

if __name__ == "__main__":
    success = test_gemini_api()
    if success:
        print("\n✅ Gemini API tests completed successfully!")
    else:
        print("\n❌ Gemini API tests failed!") 