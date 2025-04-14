"""
Simple FastAPI app with test endpoints for ISEWR
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import requests
import base64
from dotenv import load_dotenv
from google.cloud import vision
import google.generativeai as genai
from vertexai.preview.vision_models import Image, ImageCaptioningModel

# Load environment variables
load_dotenv()

app = FastAPI()

# Define models
class ImageRequest(BaseModel):
    image_url: str

class ProductRequest(BaseModel):
    object_name: str
    image_url: Optional[str] = None

class ImageResponse(BaseModel):
    success: bool
    objects: List[str] = []
    texts: List[str] = []
    scene_description: str = ""
    web_matches: List[Dict[str, Any]] = []

class ProductResponse(BaseModel):
    success: bool
    products: List[Dict[str, Any]] = []

class CelebrityResponse(BaseModel):
    success: bool
    celebrities: List[str] = []
    scene_description: str = ""

# Simple root endpoint
@app.get("/")
def read_root():
    return {"message": "ISEWR Test API is running"}

# Test Vision API
@app.post("/test-vision", response_model=ImageResponse)
def test_vision(request: ImageRequest):
    try:
        # Initialize Vision client
        client = vision.ImageAnnotatorClient()
        
        # Download the image
        response = requests.get(request.image_url)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download image")
        
        image_content = response.content
        
        # Create Vision API image
        image = vision.Image(content=image_content)
        
        # Detect labels (objects)
        objects = []
        try:
            label_detection = client.label_detection(image=image)
            labels = label_detection.label_annotations
            objects = [label.description for label in labels]
        except Exception as label_error:
            print(f"Error detecting labels: {label_error}")
        
        # Extract text (OCR)
        texts = []
        try:
            text_detection = client.text_detection(image=image)
            if text_detection.text_annotations:
                # The first result contains the entire OCR text
                texts = [text_detection.text_annotations[0].description] if text_detection.text_annotations else []
        except Exception as text_error:
            print(f"Error extracting text: {text_error}")
        
        # Web detection for similar images
        web_matches = []
        try:
            web_detection = client.web_detection(image=image)
            
            # Get web entities
            if hasattr(web_detection, 'web_detection') and hasattr(web_detection.web_detection, 'web_entities'):
                for entity in web_detection.web_detection.web_entities:
                    if entity.score >= 0.5:  # Only include entities with good confidence
                        web_matches.append({
                            "description": entity.description,
                            "score": float(entity.score)
                        })
        except Exception as web_error:
            print(f"Error in web detection: {web_error}")
        
        # Visual captioning with Gemini Pro Vision
        scene_description = ""
        try:
            # Configure the model
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            
            # Load the model
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Prepare the image data
            image_parts = [
                {
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(image_content).decode('utf-8')
                }
            ]
            
            # Generate caption
            prompt = "Describe this image in detail with one paragraph."
            response = model.generate_content([prompt, image_parts[0]])
            
            scene_description = response.text.strip()
        except Exception as e:
            print(f"Error in scene description: {e}")
            scene_description = "Unable to generate scene description."
        
        return ImageResponse(
            success=True,
            objects=objects,
            texts=texts,
            scene_description=scene_description,
            web_matches=web_matches
        )
    
    except Exception as e:
        print(f"Error in vision test: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

# Test Gemini API
@app.post("/test-gemini", response_model=CelebrityResponse)
def test_gemini(request: ImageRequest):
    try:
        # Download the image
        response = requests.get(request.image_url)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download image")
        
        image_content = response.content
        
        # Configure the Gemini API - only use the API key parameter
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Load the Gemini Pro Vision model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare the image for Gemini
        image_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_content).decode('utf-8')
            }
        ]
        
        # Generate response from Gemini with simplified prompt
        prompt = """
        Look at this image carefully and:
        1. Identify any celebrities or famous people
        2. Describe the scene briefly
        
        If you don't recognize any celebrities, just say 'No celebrities detected'.
        """
        
        response = model.generate_content([prompt, image_parts[0]])
        
        # Process the response in a simpler way
        response_text = response.text.strip()
        
        # Extract celebrities
        celebrities = []
        scene_description = response_text
        
        # Check for "No celebrities detected" pattern
        if "No celebrities detected" in response_text or "no celebrities" in response_text.lower():
            celebrities = []
            # Try to extract just the scene description part
            scene_description = response_text.replace("No celebrities detected.", "").strip()
        else:
            # Look for celebrity names - simple approach
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and (":" not in line) and len(line.split()) <= 5 and not line.startswith("I "):
                    celebrities.append(line)
        
        # Return the response
        return CelebrityResponse(
            success=True,
            celebrities=celebrities,
            scene_description=scene_description
        )
    
    except Exception as e:
        print(f"Error in celebrity identification: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing Gemini: {str(e)}")

# Test Product Search
@app.post("/test-products", response_model=ProductResponse)
def test_products(request: ProductRequest):
    try:
        object_name = request.object_name
        search_term = object_name.strip()
        products = []
        
        # Create a basic web search (fallback method)
        search_query = f"{search_term} buy online"
        
        # Provide links to help users find products related to their search term
        products = [
            {
                "name": f"{search_term} - Google Shopping",
                "url": f"https://www.google.com/search?q={search_query.replace(' ', '+')}&tbm=shop",
                "price": "Various prices",
                "store": "Google Shopping",
                "score": 0.8
            },
            {
                "name": f"{search_term} - Amazon",
                "url": f"https://www.amazon.com/s?k={search_term.replace(' ', '+')}",
                "price": "Various prices",
                "store": "Amazon",
                "score": 0.7
            },
            {
                "name": f"{search_term} - eBay",
                "url": f"https://www.ebay.com/sch/i.html?_nkw={search_term.replace(' ', '+')}",
                "price": "Various prices",
                "store": "eBay",
                "score": 0.6
            }
        ]
        
        return ProductResponse(
            success=True,
            products=products
        )
    
    except Exception as e:
        print(f"Error in product search: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing products: {str(e)}")

# Test Imagen
@app.post("/test-imagen")
def test_imagen(request: ImageRequest):
    try:
        # Download the image
        response = requests.get(request.image_url)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download image")
        
        image_content = response.content
        
        # Save the image temporarily
        test_image_path = "test_imagen_image.jpg"
        with open(test_image_path, "wb") as f:
            f.write(image_content)
            
        try:
            # Initialize Vertex AI
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            
            # Load the image captioning model
            model = ImageCaptioningModel.from_pretrained("imagetext@001")
            
            # Generate a caption using the proper Image class
            image = Image.load_from_file(test_image_path)
            captions = model.get_captions(
                image=image,
                # Optional parameters
                number_of_results=1,
                language="en"
            )
            
            # Clean up the temporary image file
            if os.path.exists(test_image_path):
                os.remove(test_image_path)
                
            return {"success": True, "caption": captions[0] if captions else "No caption generated"}
            
        except Exception as e:
            if os.path.exists(test_image_path):
                os.remove(test_image_path)
            raise e
    
    except Exception as e:
        print(f"Error testing Imagen API: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing Imagen: {str(e)}")

# Run the app with: uvicorn test_endpoints:app --reload 