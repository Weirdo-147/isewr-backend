"""
Test Google Cloud Vision API with local image
"""
import os
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from google.cloud import vision

# Load environment variables
load_dotenv()

def download_test_image(url="https://picsum.photos/200", save_path="test_image.jpg"):
    """Download a test image from URL and save locally"""
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error downloading image: HTTP {response.status_code}")
            return False
            
        with open(save_path, "wb") as f:
            f.write(response.content)
            
        print(f"Test image downloaded and saved to {save_path}")
        return True
    except Exception as e:
        print(f"Error downloading test image: {e}")
        return False

def test_vision_api():
    """Test Vision API with a local image file"""
    print("Testing Google Cloud Vision API with local image...")
    
    # Check if credentials are set
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path or not os.path.exists(credentials_path):
        print(f"Error: GOOGLE_APPLICATION_CREDENTIALS not set or file not found at: {credentials_path}")
        return False
        
    # Download a test image if we don't have one
    test_image_path = "test_image.jpg"
    if not os.path.exists(test_image_path):
        if not download_test_image(save_path=test_image_path):
            return False
    
    try:
        # Initialize Vision client
        client = vision.ImageAnnotatorClient()
        
        # Read the image file
        with open(test_image_path, "rb") as image_file:
            content = image_file.read()
        
        # Create Vision API image
        image = vision.Image(content=content)
        
        # Perform label detection
        response = client.label_detection(image=image)
        labels = response.label_annotations
        
        if not labels:
            print("No labels detected in the image. The API response was successful but didn't find any labels.")
        else:
            print(f"Successfully detected {len(labels)} labels:")
            for label in labels[:5]:  # Print first 5 labels
                print(f"- {label.description} ({label.score:.2f})")
                
        # Also test text detection
        text_response = client.text_detection(image=image)
        texts = text_response.text_annotations
        
        if texts:
            print("\nDetected text:")
            # The first annotation contains all text
            print(texts[0].description[:100] + "..." if len(texts[0].description) > 100 else texts[0].description)
            
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