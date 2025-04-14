"""
Test script to verify all API implementations individually
"""
import os
import requests
import base64
from dotenv import load_dotenv
import json
import subprocess

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
        # Run the test_imagen_simple.py script directly
        result = subprocess.run(["python", "test_imagen_simple.py"], capture_output=True, text=True)
        
        print(result.stdout)
        
        return "Vertex AI Imagen test successful" in result.stdout
    
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

if __name__ == "__main__":
    # Run each test and collect results
    print("Testing all APIs, assuming server is already running on http://localhost:8000")
    
    vision_success = test_vision_api()
    gemini_success = test_gemini_api()
    imagen_success = test_imagen_api()
    product_success = test_product_search()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Vision API: {'✅ Passed' if vision_success else '❌ Failed'}")
    print(f"Gemini API: {'✅ Passed' if gemini_success else '❌ Failed'}")
    print(f"Imagen API: {'✅ Passed' if imagen_success else '❌ Failed'}")
    print(f"Product Search: {'✅ Passed' if product_success else '❌ Failed'}")
    
    # Overall result
    overall_success = vision_success and gemini_success and imagen_success and product_success
    print(f"\nOverall Test Result: {'✅ PASSED' if overall_success else '❌ FAILED'}") 