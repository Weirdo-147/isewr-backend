"""
Test script for the separate test_endpoints.py server
"""
import requests
import json
import time

def test_vision():
    """Test Vision API endpoint"""
    print("\n=== Testing Vision API ===")
    
    try:
        # Make request to the test endpoint
        image_url = "https://picsum.photos/800/600"
        
        response = requests.post(
            "http://localhost:8001/test-vision",
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
            
        print(f"\nScene description: {result.get('scene_description', '')[:200]}...")
        
        return True
    
    except Exception as e:
        print(f"Error testing Vision API: {e}")
        return False

def test_gemini():
    """Test Gemini API endpoint"""
    print("\n=== Testing Gemini API ===")
    
    try:
        # Make request to the test endpoint
        image_url = "https://picsum.photos/800/600"
        
        response = requests.post(
            "http://localhost:8001/test-gemini",
            json={"image_url": image_url}
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

def test_imagen():
    """Test Imagen API endpoint"""
    print("\n=== Testing Imagen API ===")
    
    try:
        # Make request to the test endpoint
        image_url = "https://picsum.photos/800/600"
        
        response = requests.post(
            "http://localhost:8001/test-imagen",
            json={"image_url": image_url}
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return False
        
        result = response.json()
        
        print("Imagen API Caption:")
        print(f"- {result.get('caption', 'No caption generated')}")
        
        return True
    
    except Exception as e:
        print(f"Error testing Imagen API: {e}")
        return False

def test_products():
    """Test Product Search endpoint"""
    print("\n=== Testing Product Search ===")
    
    try:
        # Make request to the test endpoint
        object_name = "camera"
        
        response = requests.post(
            "http://localhost:8001/test-products",
            json={"object_name": object_name}
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return False
        
        result = response.json()
        
        print(f"Products found for '{object_name}':")
        for product in result.get("products", []):
            print(f"- {product.get('name')} ({product.get('store')})")
        
        return True
    
    except Exception as e:
        print(f"Error testing Product Search: {e}")
        return False

if __name__ == "__main__":
    # Wait for server to be ready
    print("Testing the test_endpoints server...")
    
    # Try to check if server is ready
    max_retries = 5
    server_ready = False
    
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8001/")
            if response.status_code == 200:
                server_ready = True
                print("Server is ready!")
                break
        except:
            pass
        
        print(f"Waiting for server to start (attempt {i+1}/{max_retries})...")
        time.sleep(3)
    
    if not server_ready:
        print("Server is not ready. Make sure to run 'uvicorn test_endpoints:app --host 0.0.0.0 --port 8001'")
        exit(1)
    
    # Run the tests
    vision_success = test_vision()
    gemini_success = test_gemini()
    imagen_success = test_imagen()
    products_success = test_products()
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Vision API: {'✓ Passed' if vision_success else '✗ Failed'}")
    print(f"Gemini API: {'✓ Passed' if gemini_success else '✗ Failed'}")
    print(f"Imagen API: {'✓ Passed' if imagen_success else '✗ Failed'}")
    print(f"Product Search: {'✓ Passed' if products_success else '✗ Failed'}")
    
    # Overall result
    overall_success = vision_success and gemini_success and imagen_success and products_success
    print(f"\nOverall Result: {'PASSED' if overall_success else 'FAILED'}") 