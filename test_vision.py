"""
Test Google Cloud Vision API connection
"""
import os
import requests
from dotenv import load_dotenv
from google.cloud import vision

# Load environment variables
load_dotenv()

def test_vision_api():
    """Test basic Vision API label detection"""
    print("Testing Google Cloud Vision API...")
    
    # Check for credentials file
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path or not os.path.exists(credentials_path):
        print(f"Error: GOOGLE_APPLICATION_CREDENTIALS not set or file not found at: {credentials_path}")
        return False
    
    try:
        # Initialize the client
        client = vision.ImageAnnotatorClient()
        
        # Download a sample image
        image_url = "https://picsum.photos/200"
        response = requests.get(image_url)
        if response.status_code != 200:
            print(f"Error downloading test image: HTTP {response.status_code}")
            return False
        
        image_content = response.content
        
        # Create Vision API image
        image = vision.Image(content=image_content)
        
        # Detect labels
        response = client.label_detection(image=image)
        
        # Print the detected labels
        labels = response.label_annotations
        print(f"Successfully detected {len(labels)} labels:")
        for label in labels[:3]:  # Just print the top 3
            print(f"- {label.description} ({label.score:.2f})")
        
        # Check for product search capability
        try:
            # This is to check if product_searches is available in the API version
            web_detection = client.web_detection(image=image)
            product_searches_available = hasattr(web_detection.web_detection, 'product_searches')
            print(f"Product searches capability available: {product_searches_available}")
            
            if not product_searches_available:
                print("Note: product_searches is not available in your Vision API version")
                print("Web entities available instead: {bool(web_detection.web_detection.web_entities)}")
        except Exception as web_error:
            print(f"Error checking web detection: {web_error}")
        
        return True
    
    except Exception as e:
        print(f"Error testing Vision API: {e}")
        return False

if __name__ == "__main__":
    success = test_vision_api()
    if success:
        print("✅ Vision API test successful!")
    else:
        print("❌ Vision API test failed!") 