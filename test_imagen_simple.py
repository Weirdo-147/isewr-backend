"""
Test Vertex AI Imagen API for scene captioning (simplified)
"""
import os
import requests
import time
from dotenv import load_dotenv
from google.cloud import aiplatform
from vertexai.preview.vision_models import Image, ImageCaptioningModel

# Load environment variables
load_dotenv()

def test_imagen_captioning():
    """Test Vertex AI Imagen image captioning"""
    print("Testing Vertex AI Imagen image captioning...")
    
    # Check if Google Cloud credentials are set
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path or not os.path.exists(credentials_path):
        print(f"Error: GOOGLE_APPLICATION_CREDENTIALS not set or file not found at: {credentials_path}")
        return False
    
    # Check project ID
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        print("Error: GOOGLE_CLOUD_PROJECT not set in environment variables")
        return False
    
    try:
        # Initialize Vertex AI
        aiplatform.init(project=project_id)
        
        # Download a sample image
        print("Downloading a test image...")
        image_url = "https://picsum.photos/800/600"
        response = requests.get(image_url)
        if response.status_code != 200:
            print(f"Error downloading test image: HTTP {response.status_code}")
            return False
        
        # Save the image temporarily
        test_image_path = "test_imagen_image.jpg"
        with open(test_image_path, "wb") as f:
            f.write(response.content)
        
        print(f"Image downloaded and saved to {test_image_path}")
        
        # Load the image captioning model
        model = ImageCaptioningModel.from_pretrained("imagetext@001")
        
        # Generate a caption using the proper Image class
        print("Generating image caption...")
        image = Image.load_from_file(test_image_path)
        captions = model.get_captions(
            image=image,
            # Optional parameters
            number_of_results=1,
            language="en"
        )
        
        # Display the results
        print("\nGenerated Caption:")
        for caption in captions:
            print(f"- {caption}")
        
        return True
    
    except Exception as e:
        print(f"Error testing Vertex AI Imagen: {e}")
        return False
    finally:
        # Clean up the temporary image file
        if os.path.exists(test_image_path):
            os.remove(test_image_path)

if __name__ == "__main__":
    success = test_imagen_captioning()
    if success:
        print("Vertex AI Imagen test successful!")
    else:
        print("Vertex AI Imagen test failed!")