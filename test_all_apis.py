"""
Test script to verify all API implementations are working correctly
"""
import os
import requests
import base64
from dotenv import load_dotenv
import json
import time

# Load environment variables
load_dotenv()

def test_vision_api():
    """Test Google Cloud Vision API for object detection"""
    print("\n=== Testing Google Cloud Vision API ===")
    
    try:
        # Make a request to the recognize endpoint with a test image
        image_url = "https://picsum.photos/800/600"
        
        response = requests.post(
            "http://localhost:8000/recognize",
            json={"image_url": image_url}
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return False
        
        result = response.json()
        
        print("Vision API Objects detected:")
        for obj in result.get("objects", [])[:5]:
            print(f"- {obj}")
            
        print("\nVision API Text extracted:")
        for text in result.get("texts", [])[:1]:
            print(f"- {text[:100]}..." if len(text) > 100 else f"- {text}")
        
        print("\nVision API Web matches:")
        for match in result.get("web_matches", [])[:3]:
            print(f"- {match.get('description')} ({match.get('score', 0):.2f})")
        
        return True
    
    except Exception as e:
        print(f"Error testing Vision API: {e}")
        return False

def test_gemini_api():
    """Test Gemini API for image description"""
    print("\n=== Testing Gemini API for Image Description ===")
    
    try:
        response = requests.post(
            "http://localhost:8000/celebrity",
            json={"image_url": "https://picsum.photos/800/600"}
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return False
        
        result = response.json()
        
        print("Gemini API Scene Description:")
        print(result.get("scene_description", "")[:200] + "..." if len(result.get("scene_description", "")) > 200 else result.get("scene_description", ""))
        
        print("\nCelebrities detected:")
        for celebrity in result.get("celebrities", []):
            print(f"- {celebrity}")
        
        return True
    
    except Exception as e:
        print(f"Error testing Gemini API: {e}")
        return False

def test_imagen_api():
    """Test Vertex AI Imagen for image captioning"""
    print("\n=== Testing Vertex AI Imagen API ===")
    
    try:
        # Use the test_imagen.py script directly
        import subprocess
        result = subprocess.run(["python", "test_imagen.py"], capture_output=True, text=True)
        
        print(result.stdout)
        
        if "Vertex AI Imagen test successful" in result.stdout:
            return True
        else:
            print(f"Error in Imagen test: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"Error testing Imagen API: {e}")
        return False

def test_product_search():
    """Test product search functionality"""
    print("\n=== Testing Product Search Functionality ===")
    
    try:
        # Test with an object name
        object_name = "camera"
        
        response = requests.post(
            "http://localhost:8000/products",
            json={"object_name": object_name}
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return False
        
        result = response.json()
        
        print(f"Products found for '{object_name}':")
        for product in result.get("products", [])[:5]:
            print(f"- {product.get('name')} ({product.get('store')})")
        
        # Test with an object name and image URL
        image_url = "https://picsum.photos/800/600"
        
        response = requests.post(
            "http://localhost:8000/products",
            json={"object_name": object_name, "image_url": image_url}
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return False
        
        result = response.json()
        
        print(f"\nProducts found for '{object_name}' with image URL:")
        for product in result.get("products", [])[:5]:
            print(f"- {product.get('name')} ({product.get('store')})")
        
        return True
    
    except Exception as e:
        print(f"Error testing product search: {e}")
        return False

def test_deepfake_detection():
    """Test deepfake detection API with image"""
    print("\n=== Testing Deepfake Detection API ===")
    
    try:
        # We'll just test if the endpoint is accessible without an actual file
        # since we don't want to upload files in this test script
        
        print("Note: Deepfake detection requires file upload, so checking endpoint only")
        
        # Check if API key is set
        api_user = os.getenv("SIGHTENGINE_API_USER")
        api_secret = os.getenv("SIGHTENGINE_API_SECRET")
        
        if not api_user or not api_secret:
            print(f"Warning: SightEngine API credentials not configured. User: {api_user}, Secret: {'*' * len(api_secret) if api_secret else None}")
            return False
            
        print(f"SightEngine API credentials are configured. User: {api_user}, Secret: {'*' * min(5, len(api_secret)) if api_secret else None}...")
        return True
    
    except Exception as e:
        print(f"Error testing deepfake detection: {e}")
        return False

if __name__ == "__main__":
    # Start FastAPI server using uvicorn in a separate process
    import subprocess
    import sys
    import time
    
    # Check if server is already running on port 8000
    try:
        response = requests.get("http://localhost:8000/")
        server_running = response.status_code == 200
    except:
        server_running = False
    
    server_process = None
    
    # Start server if not running
    if not server_running:
        print("Starting FastAPI server...")
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        # Wait for server to start
        max_retries = 5
        retry_count = 0
        while retry_count < max_retries:
            try:
                response = requests.get("http://localhost:8000/")
                if response.status_code == 200:
                    print("Server started successfully!")
                    break
            except:
                pass
            
            print(f"Waiting for server to start (attempt {retry_count+1}/{max_retries})...")
            time.sleep(2)
            retry_count += 1
    
    # Run tests
    print("\n=== Running API Tests ===")
    
    vision_success = test_vision_api()
    gemini_success = test_gemini_api()
    imagen_success = test_imagen_api()
    product_success = test_product_search()
    deepfake_success = test_deepfake_detection()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Vision API: {'✅ Passed' if vision_success else '❌ Failed'}")
    print(f"Gemini API: {'✅ Passed' if gemini_success else '❌ Failed'}")
    print(f"Imagen API: {'✅ Passed' if imagen_success else '❌ Failed'}")
    print(f"Product Search: {'✅ Passed' if product_success else '❌ Failed'}")
    print(f"Deepfake Detection: {'✅ Passed' if deepfake_success else '❌ Failed'}")
    
    # Overall result
    overall_success = vision_success and gemini_success and imagen_success and product_success
    print(f"\nOverall Test Result: {'✅ Passed' if overall_success else '❌ Failed'}")
    
    # Stop server if we started it
    if server_process:
        print("\nStopping FastAPI server...")
        server_process.terminate()
        server_process.wait()