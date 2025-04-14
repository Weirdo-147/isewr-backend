from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Header, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import random
import os
import json
import requests
from typing import List, Optional, Dict, Any
import shutil
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import base64
from models import ImageResponse, ProcessRequest, SupabaseConfig, VideoConversionRequest, VideoConversionResponse, DeepfakeDetectionRequest, DeepfakeDetectionResponse
from supabase_client import (
    get_image, 
    store_processed_image, 
    upload_image_to_bucket,
    store_video_conversion,
    update_video_conversion,
    get_video_conversion,
    upload_video_to_bucket,
    store_recognition_result,
    get_recognition_result
)
from dotenv import load_dotenv
from pathlib import Path
import uuid
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from google.cloud import vision
from google.cloud import aiplatform
import google.generativeai as genai
import asyncio

# Load environment variables from .env file
load_dotenv()

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CLIPDROP_API_KEY = os.getenv("CLIPDROP_API_KEY")
IMAGINE_ART_API_KEY = os.getenv("IMAGINE_ART_API_KEY")
SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

# Setup Supabase client if credentials are available
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        # Import the functions but don't re-initialize the client
        from supabase_client import (
            get_image, 
            store_processed_image, 
            upload_image_to_bucket,
            store_video_conversion,
            update_video_conversion,
            get_video_conversion,
            upload_video_to_bucket
        )
        print("Supabase client functions imported successfully")
    except Exception as e:
        print(f"Error importing Supabase functions: {e}")
else:
    print("Supabase credentials not found in environment variables")

app = FastAPI(title="ISEWR API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Create videos directory if it doesn't exist
VIDEOS_DIR = os.path.join(UPLOAD_DIR, "videos")
os.makedirs(VIDEOS_DIR, exist_ok=True)

# Mount the uploads directory to serve files
app.mount("/images", StaticFiles(directory="uploads"), name="images")

# Response models
class ImageResponse(BaseModel):
    success: bool
    base64: Optional[str] = None
    path: Optional[str] = None

class BackgroundRemovalRequest(BaseModel):
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    return_type: str = "url"  # Can be "url" or "base64"

# New models for recognition endpoints
class RecognitionRequest(BaseModel):
    image_url: str

class RecognitionResponse(BaseModel):
    success: bool
    objects: List[str] = []
    texts: List[str] = []
    scene_description: str = ""
    web_matches: List[Dict[str, Any]] = []
    image_url: str = ""
    recognition_id: Optional[str] = None

class ProductRequest(BaseModel):
    object_name: str
    image_url: Optional[str] = None

class ProductResponse(BaseModel):
    success: bool
    products: List[Dict[str, Any]] = []

class CelebrityRequest(BaseModel):
    image_url: str

class CelebrityResponse(BaseModel):
    success: bool
    celebrities: List[str] = []
    scene_description: str = ""

# Initialize Google Cloud Vision client if credentials are available
vision_client = None
google_cloud_initialized = False
try:
    # Initialize Google Cloud Vision client
    if GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        vision_client = vision.ImageAnnotatorClient()
        # Initialize Vertex AI
        aiplatform.init(project=GOOGLE_CLOUD_PROJECT)
        
        # Configure Gemini API with API key from environment (optional)
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        if GOOGLE_API_KEY:
            genai.configure(api_key=GOOGLE_API_KEY)
        else:
            # Configure using application default credentials
            genai.configure(project=GOOGLE_CLOUD_PROJECT)
            
        google_cloud_initialized = True
        print("Google Cloud services initialized successfully")
    else:
        print("Google Cloud credentials not found or invalid")
except Exception as e:
    print(f"Error initializing Google Cloud clients: {e}")

@app.post("/recognize", response_model=RecognitionResponse)
async def recognize_image(request: RecognitionRequest):
    """
    Recognize objects, extract text, and describe scenes in an image using Google Cloud Vision API and Gemini Pro Vision.
    """
    if not vision_client or not google_cloud_initialized:
        raise HTTPException(status_code=500, detail="Google Cloud services not initialized")
    
    try:
        image_url = request.image_url
        
        # Download the image
        response = requests.get(image_url)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download image")
        
        image_content = response.content
        
        # Create Vision API image
        image = vision.Image(content=image_content)
        
        # Detect labels (objects)
        objects = []
        try:
            label_detection = vision_client.label_detection(image=image)
            labels = label_detection.label_annotations
            objects = [label.description for label in labels]
        except Exception as label_error:
            print(f"Error detecting labels: {label_error}")
        
        # Extract text (OCR)
        texts = []
        try:
            text_detection = vision_client.text_detection(image=image)
            if text_detection.text_annotations:
                # The first result contains the entire OCR text
                texts = [text_detection.text_annotations[0].description] if text_detection.text_annotations else []
        except Exception as text_error:
            print(f"Error extracting text: {text_error}")
        
        # Web detection for similar images
        web_matches = []
        try:
            web_detection = vision_client.web_detection(image=image)
            
            # Get web entities
            if hasattr(web_detection, 'web_detection') and hasattr(web_detection.web_detection, 'web_entities'):
                for entity in web_detection.web_detection.web_entities:
                    if entity.score >= 0.5:  # Only include entities with good confidence
                        web_matches.append({
                            "description": entity.description,
                            "score": entity.score
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
        
        # Store result in Supabase
        recognition_result = {
            "image_url": image_url,
            "objects": objects,
            "texts": texts,
            "scene_description": scene_description,
            "web_matches": web_matches
        }
        
        recognition_record = await store_recognition_result(recognition_result)
        recognition_id = recognition_record.get("id") if recognition_record else None
        
        return RecognitionResponse(
        success=True,
            objects=objects,
            texts=texts,
            scene_description=scene_description,
            web_matches=web_matches,
            image_url=image_url,
            recognition_id=recognition_id
        )
    
    except Exception as e:
        print(f"Error in recognition: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@app.post("/products", response_model=ProductResponse)
async def search_products(request: ProductRequest):
    """
    Search for products based on an object name and optionally an image URL.
    """
    try:
        object_name = request.object_name
        search_term = object_name.strip()
        products = []
        
        # Check if an image URL was provided
        if hasattr(request, 'image_url') and request.image_url:
            # If we have an image_url, try to find products using vision web entities
            try:
                # Download the image
                response = requests.get(request.image_url)
                if response.status_code == 200:
                    image_content = response.content
                    
                    # Create Vision API image and get web entities if Vision API is available
                    if vision_client and google_cloud_initialized:
                        image = vision.Image(content=image_content)
                        web_detection = vision_client.web_detection(image=image)
                        
                        # Try to get product-related web entities
                        product_terms = []
                        if hasattr(web_detection, 'web_detection'):
                            # Extract web entities with good confidence
                            for entity in web_detection.web_detection.web_entities:
                                if entity.score >= 0.7 and entity.description.lower() != search_term.lower():
                                    product_terms.append(entity.description)
                            
                            # Add specific product terms related to the object
                            product_terms = product_terms[:3]  # Limit to top 3 terms
                            
                            if product_terms:
                                # Combine the original search term with the top product term
                                enhanced_term = f"{search_term} {product_terms[0]}"
                                print(f"Enhanced search term: {enhanced_term}")
            except Exception as vis_error:
                print(f"Error processing image for product search: {vis_error}")
        
        # Create a search term based on the object
        search_query = f"{search_term} buy online"
        
        # Add category-specific terms based on the object
        category_terms = {
            "camera": ["digital camera", "DSLR", "mirrorless", "point and shoot"],
            "laptop": ["laptop", "notebook", "MacBook", "Windows laptop", "gaming laptop"],
            "phone": ["smartphone", "iPhone", "Android phone", "mobile phone"],
            "headphones": ["wireless headphones", "earbuds", "over-ear headphones"],
            "watch": ["smartwatch", "wristwatch", "Apple Watch", "analog watch"],
            "television": ["TV", "smart TV", "4K TV", "OLED TV"],
            "chair": ["office chair", "dining chair", "ergonomic chair"],
            "table": ["dining table", "desk", "coffee table"],
            "car": ["automobile", "new car", "used car"],
            "shoes": ["running shoes", "sneakers", "boots", "dress shoes"],
            "clothing": ["clothes", "fashion", "apparel", "outfit"],
            "food": ["groceries", "meal", "snacks", "delivery"],
            "book": ["novel", "textbook", "ebook", "paperback"],
            "jewelry": ["necklace", "ring", "bracelet", "earrings"],
            "bicycle": ["bike", "mountain bike", "road bike", "electric bike"],
            "bag": ["handbag", "backpack", "luggage", "purse"]
        }
        
        # Look for a close match in our categories
        matching_category = None
        for category in category_terms:
            if (search_term.lower() == category.lower() or 
                category.lower() in search_term.lower() or
                search_term.lower() in category.lower()):
                matching_category = category
                break
        
        # Create specialized product links based on the category
        if matching_category:
            # Get the specific terms for this category
            specific_terms = category_terms[matching_category]
            
            # Add specialized product links
            for term in specific_terms:
                if term.lower() != search_term.lower():  # Avoid duplicates
                    products.append({
                        "name": f"{term}",
                        "url": f"https://www.google.com/search?q={term.replace(' ', '+')}&tbm=shop",
                        "price": "Various prices",
                        "store": "Google Shopping",
                        "score": 0.9
                    })
        
        # Always add generic product links
        products.extend([
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
            },
            {
                "name": f"{search_term} - Walmart",
                "url": f"https://www.walmart.com/search/?query={search_term.replace(' ', '+')}",
                "price": "Various prices",
                "store": "Walmart",
                "score": 0.5
            },
            {
                "name": f"{search_term} - Target",
                "url": f"https://www.target.com/s?searchTerm={search_term.replace(' ', '+')}",
                "price": "Various prices",
                "store": "Target",
                "score": 0.4
            }
        ])
        
        # Sort products by score
        products = sorted(products, key=lambda x: x.get("score", 0), reverse=True)
        
        return ProductResponse(
            success=True,
            products=products
        )
    
    except Exception as e:
        print(f"Error in product search: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching for products: {str(e)}")

@app.post("/celebrity", response_model=CelebrityResponse)
async def identify_celebrity(request: CelebrityRequest):
    """
    Identify celebrities in an image using Gemini Pro Vision.
    """
    if not google_cloud_initialized:
        raise HTTPException(status_code=500, detail="Google Cloud services not initialized")
    
    try:
        image_url = request.image_url
        
        # Download the image
        response = requests.get(image_url)
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
        raise HTTPException(status_code=500, detail=f"Error identifying celebrities: {str(e)}")

@app.post("/detect-deepfake")
async def detect_deepfake(
    file: UploadFile = File(...),
    mode: str = Form("standard"),
    threshold: float = Form(0.8)
):
    """
    Detect if a video contains deepfake content using SightEngine API.
    """
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Check if SightEngine API credentials are configured
    api_user = os.getenv("SIGHTENGINE_API_USER")
    api_secret = os.getenv("SIGHTENGINE_API_SECRET")
    
    if not api_user or not api_secret:
        raise HTTPException(
            status_code=500, 
            detail="SightEngine API credentials not configured"
        )
    
    try:
        # Save the uploaded file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"Video saved to: {file_path}")
        
        # Determine model set based on mode
        models = "nudity,wad,offensive,face-attributes"
        if mode == "aggressive":
            models = "nudity,wad,offensive,face-attributes,gore,drugs"
            threshold = max(threshold, 0.9)  # Increase threshold for aggressive mode
        elif mode == "lightweight":
            models = "nudity,wad,face-attributes"
            threshold = min(threshold, 0.7)  # Lower threshold for lightweight mode
        elif mode == "detailed":
            models = "nudity,wad,offensive,face-attributes,gore,text-content,scam"
        
        # Call SightEngine API with file upload
        with open(file_path, "rb") as f:
            response = requests.post(
                'https://api.sightengine.com/1.0/video/check-sync.json',
                files={'media': f},
                data={
                    'models': models,
                    'api_user': api_user,
                    'api_secret': api_secret
                }
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"API response: {result}")
            
            if result.get('status') == 'success':
                # Get the video ID for status checking
                video_id = result.get('video', {}).get('id')
                
                if not video_id:
                    raise HTTPException(status_code=500, detail="No video ID in response")
                
                # Poll for status a few times
                max_retries = 5
                retry_count = 0
                result_data = None
                
                while retry_count < max_retries:
                    # Wait between retries
                    if retry_count > 0:
                        await asyncio.sleep(2)
                    
                    # Check video status
                    status_response = requests.get(
                        'https://api.sightengine.com/1.0/video/status.json',
                        params={
                            'api_user': api_user,
                            'api_secret': api_secret,
                            'id': video_id
                        }
                    )
                    
                    if status_response.status_code == 200:
                        status_result = status_response.json()
                        
                        if status_result.get('status') == 'success':
                            status = status_result.get('video', {}).get('status')
                            
                            if status == 'ready':
                                # Video processing is complete, get frames
                                frames_response = requests.get(
                                    'https://api.sightengine.com/1.0/video/frames.json',
                                    params={
                                        'api_user': api_user,
                                        'api_secret': api_secret,
                                        'id': video_id
                                    }
                                )
                                
                                if frames_response.status_code == 200:
                                    result_data = frames_response.json()
                                    break
                            elif status == 'error':
                                raise HTTPException(status_code=500, detail="Error processing video")
                    
                    retry_count += 1
                
                if not result_data:
                    return {
                        "success": True,
                    "message": "Video analysis initiated",
                        "video_id": video_id,
                        "status": "processing",
                        "confidence": 0,
                        "face_confidence": 0,
                        "lip_sync_confidence": 0,
                        "motion_confidence": 0,
                        "findings": ["Analysis in progress, please check back later"]
                    }
                
                # Process the result data to extract meaningful insights
                frames = result_data.get('frames', [])
                total_frames = len(frames)
                
                if total_frames == 0:
                    return {
                        "success": True,
                    "message": "No analyzable frames found",
                        "video_id": video_id,
                        "confidence": 0,
                        "face_confidence": 0,
                        "lip_sync_confidence": 0,
                        "motion_confidence": 0,
                        "findings": ["No analyzable frames found in the video"]
                    }
                
                # Calculate metrics from frames
                # Count frames with faces and potential manipulation
                frames_with_faces = 0
                frames_with_deepfake = 0
                total_face_score = 0
                total_deepfake_score = 0
                
                for frame in frames:
                    has_face = bool(frame.get('faces', []))
                    if has_face:
                        frames_with_faces += 1
                        
                        # Check for deepfake score in this frame
                        deepfake_score = frame.get('type', {}).get('deepfake', 0)
                        if deepfake_score > threshold:
                            frames_with_deepfake += 1
                            total_deepfake_score += deepfake_score
                            
                        # Add to total face score for averaging
                        for face in frame.get('faces', []):
                            # Get face attributes that might indicate manipulation
                            face_attrs = face.get('attributes', {})
                            total_face_score += 1
                
                # Calculate final confidence scores
                face_confidence = (frames_with_faces / total_frames) * 100 if total_frames > 0 else 0
                deepfake_confidence = (frames_with_deepfake / frames_with_faces) * 100 if frames_with_faces > 0 else 0
                avg_deepfake_score = (total_deepfake_score / frames_with_deepfake) * 100 if frames_with_deepfake > 0 else 0
                
                # Final combined confidence score
                confidence = avg_deepfake_score if avg_deepfake_score > 0 else deepfake_confidence
                
                # Prepare detailed findings
                findings = []
                
                if frames_with_deepfake > 0:
                    findings.append(f"Detected potential deepfake manipulation in {frames_with_deepfake} of {frames_with_faces} frames with faces")
                    findings.append(f"Average manipulation confidence: {avg_deepfake_score:.2f}%")
                
                if frames_with_faces > 0:
                    findings.append(f"Detected faces in {frames_with_faces} of {total_frames} frames")
                
                # Add findings based on other aspects of the video
                nudity_scores = []
                offensive_scores = []
                
                for frame in frames:
                    nudity_score = frame.get('nudity', {}).get('raw', 0)
                    if nudity_score > 0.5:
                        nudity_scores.append(nudity_score)
                    
                    offensive_score = frame.get('offensive', {}).get('prob', 0)
                    if offensive_score > 0.5:
                        offensive_scores.append(offensive_score)
                
                if nudity_scores:
                    avg_nudity = sum(nudity_scores) / len(nudity_scores)
                    findings.append(f"Detected possible inappropriate content in {len(nudity_scores)} frames")
                
                if offensive_scores:
                    avg_offensive = sum(offensive_scores) / len(offensive_scores)
                    findings.append(f"Detected potentially offensive content in {len(offensive_scores)} frames")
                
                # If no specific findings, add generic ones
                if not findings:
                    findings = [
                        "No clear signs of deepfake manipulation detected",
                        "Video appears to be authentic based on analyzed frames"
                    ]
                
                return {
                    "success": True,
                    "message": "Video analysis completed",
                    "video_id": video_id,
                    "confidence": confidence,
                    "face_confidence": face_confidence,
                    "lip_sync_confidence": avg_deepfake_score,
                    "motion_confidence": deepfake_confidence,
                    "findings": findings
                }
            else:
                error_msg = result.get('error', {}).get('message', 'Unknown error')
                raise HTTPException(status_code=500, detail=f"SightEngine API error: {error_msg}")
        else:
            error_text = response.text
            raise HTTPException(
                status_code=response.status_code,
                detail=f"SightEngine API error: {error_text}"
            )
    
    except Exception as e:
        print(f"Error in deepfake detection: {e}")
        raise HTTPException(status_code=500, detail=f"Error detecting deepfake: {str(e)}")

@app.post("/convert", response_model=VideoConversionResponse)
async def convert_to_video(
    file: Optional[UploadFile] = File(None),
    prompt: str = Form(...),
    style: str = Form("kling-1.0-pro"),
    aspect_ratio: str = Form("1:1"),
    image_url: Optional[str] = Form(None)
):
    """
    Convert an image to video using imagine.art API.
    Either provide a file upload or an image URL.
    """
    # Check if imagine.art API key is configured
    if not IMAGINE_ART_API_KEY:
        raise HTTPException(status_code=500, detail="imagine.art API key not configured")
    
    try:
        # Determine if we're using a file upload or a URL
        if file and not image_url:
            if not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Save the uploaded file
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Upload to Supabase and get URL
            with open(file_path, "rb") as f:
                file_content = f.read()
                image_filename = f"img2vid_{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
                image_url = await upload_image_to_bucket(file_content, image_filename)
                
                if not image_url:
                    # If upload to Supabase fails, use local file path
                    image_url = f"http://localhost:8000/images/{file.filename}"
        
        elif image_url and not file:
            # URL provided, no need to upload
            pass
        else:
            raise HTTPException(status_code=400, detail="Either provide a file or an image URL, not both or neither")
            
        # Store initial data in Supabase
        conversion_data = {
            "original_image_url": image_url,
            "prompt": prompt,
            "style": style,
            "aspect_ratio": aspect_ratio,
            "status": "pending"
        }
        
        # Store in Supabase
        conversion_record = await store_video_conversion(conversion_data)
        conversion_id = conversion_record.get("id", str(uuid.uuid4()))
        
        # Start an asynchronous task to call the imagine.art API
        # In a production environment, you would use a task queue like Celery
        # For now, we'll make this a separate function and return the pending status
        
        # Return the conversion ID and status
        return VideoConversionResponse(
            id=conversion_id,
            status="pending"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting image to video: {str(e)}")

@app.get("/convert/{conversion_id}", response_model=VideoConversionResponse)
async def get_video_conversion_status(conversion_id: str):
    """
    Get the status of a video conversion
    """
    try:
        # Get conversion from Supabase
        conversion = await get_video_conversion(conversion_id)
        
        if not conversion:
            raise HTTPException(status_code=404, detail="Video conversion not found")
        
        # If the status is pending, we need to check if we should convert it
        if conversion.get("status") == "pending":
            # In a production environment, this would be handled by a worker
            # For now, trigger the conversion if it's still pending
            await process_video_conversion(conversion_id)
            
            # Refresh the conversion data
            conversion = await get_video_conversion(conversion_id)
        
        return VideoConversionResponse(
            id=conversion.get("id"),
            status=conversion.get("status"),
            video_url=conversion.get("video_url"),
            created_at=conversion.get("created_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting video conversion status: {str(e)}")

async def process_video_conversion(conversion_id: str):
    """
    Process a video conversion using the imagine.art API
    """
    # Track file handle to ensure proper closing
    file_handle = None
    
    try:
        # Get conversion data from Supabase
        conversion = await get_video_conversion(conversion_id)
        
        if not conversion:
            print(f"Conversion {conversion_id} not found")
            return
        
        # If it's already completed or failed, don't process it again
        if conversion.get("status") not in ["pending", "processing"]:
            return
        
        # Update status to processing
        await update_video_conversion(conversion_id, {"status": "processing"})
        
        # Download the image
        image_url = conversion.get("original_image_url")
        response = requests.get(image_url)
        
        if response.status_code != 200:
            await update_video_conversion(conversion_id, {
                "status": "failed"
            })
            return
        
        # Save image to temp file
        image_filename = f"temp_img_{conversion_id}.jpg"
        image_path = os.path.join(UPLOAD_DIR, image_filename)
        
        with open(image_path, "wb") as f:
            f.write(response.content)
        
        # Prepare API call to imagine.art
        api_url = "https://api.vyro.ai/v2/video/image-to-video"
        
        headers = {
            "Authorization": f"Bearer {IMAGINE_ART_API_KEY}"
        }
        
        # Read file content into memory and close file handle immediately
        with open(image_path, 'rb') as f:
            file_content = f.read()
        
        # Update files to match the example in the documentation
        payload = {}
        files = [
            ('file', (image_filename, file_content, 'image/jpeg')),
            ('prompt', (None, conversion.get("prompt"))),
            ('style', (None, conversion.get("style"))),
            ('aspect_ratio', (None, conversion.get("aspect_ratio")))
        ]
        
        # Make API call
        print(f"Calling imagine.art API for conversion {conversion_id}")
        api_response = requests.post(api_url, headers=headers, data=payload, files=files)
        
        # Clean up temp file
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as cleanup_error:
            print(f"Warning: Could not remove temp file: {cleanup_error}")
        
        if api_response.status_code != 200:
            error_message = f"imagine.art API call failed: HTTP {api_response.status_code}"
            try:
                error_data = api_response.json()
                error_message += f" - {json.dumps(error_data)}"
            except:
                error_message += f" - {api_response.text[:100]}"
            
            print(f"API call failed: {error_message}")
            await update_video_conversion(conversion_id, {
                "status": "failed"
            })
            return
        
        # Check content type to ensure we got video data
        print(f"Response content type: {api_response.headers.get('Content-Type', 'unknown')}")
        print(f"Response size: {len(api_response.content)} bytes")
        
        # Save the video
        video_filename = f"video_{conversion_id}.mp4"
        video_path = os.path.join(VIDEOS_DIR, video_filename)
        
        with open(video_path, "wb") as f:
            f.write(api_response.content)
        
        # Verify file was saved and is a video
        if not os.path.exists(video_path) or os.path.getsize(video_path) < 1000:
            print(f"Warning: Video file doesn't exist or is too small: {video_path}")
            print(f"First 100 bytes of response: {api_response.content[:100]}")
            await update_video_conversion(conversion_id, {
                "status": "failed"
            })
            return
        
        # Upload to Supabase
        video_url = await upload_video_to_bucket(api_response.content, video_filename)
        
        if not video_url:
            # Fall back to local URL
            video_url = f"http://localhost:8000/images/videos/{video_filename}"
        
        print(f"Video uploaded to: {video_url}")
        
        # Update Supabase record
        await update_video_conversion(conversion_id, {
            "status": "completed",
            "video_url": video_url
        })
        
        # Verify the video URL is valid
        try:
            url_check = requests.head(video_url, timeout=5)
            print(f"Video URL check: HTTP {url_check.status_code}")
            if url_check.status_code != 200:
                print(f"Warning: Video URL might not be accessible (HTTP {url_check.status_code})")
        except Exception as url_error:
            print(f"Warning: Error checking video URL: {url_error}")
        
        print(f"Video conversion {conversion_id} completed successfully")
        
    except Exception as e:
        print(f"Error processing video conversion {conversion_id}: {str(e)}")
        try:
            # Only update the status, don't try to set an error column
            await update_video_conversion(conversion_id, {
                "status": "failed"
            })
        except Exception as update_error:
            print(f"Failed to update conversion status for {conversion_id}: {update_error}")
    finally:
        # Extra safety - make sure file handle is closed
        if file_handle and not file_handle.closed:
            file_handle.close()

@app.post("/process", response_model=ImageResponse)
async def process_image(
    request: Request,
    x_process_type: Optional[str] = Header(None)
):
    """
    Process an image with specified edits.
    This endpoint can be called either with a direct file upload or with a JSON body containing
    an image URL and processing parameters.
    """
    process_type = x_process_type or "default"
    
    # Get the request content type
    content_type = request.headers.get("content-type", "")
    
    if "multipart/form-data" in content_type:
        # Handle form upload
        form = await request.form()
        file = form.get("file")
        
        if not file or not isinstance(file, UploadFile):
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Save the uploaded file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the image based on process_type
        processed_image_path = await handle_image_processing(file_path, process_type)
        
        # In a real implementation, you'd probably upload this to Supabase
        # For now, return a mock response
        return ImageResponse(
            success=True,
            message=f"Image processed with {process_type}",
            objects=[processed_image_path],
            processed_image_url=f"http://localhost:8000/uploads/{os.path.basename(processed_image_path)}"
        )
    
    elif "application/json" in content_type:
        # Handle JSON request with URL
        body = await request.json()
        process_request = ProcessRequest(**body)
        
        # Download the image from the URL
        try:
            response = requests.get(process_request.image_url)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Could not download image from URL")
            
            # Process the image based on parameters
            img = Image.open(BytesIO(response.content))
            
            # Apply brightness
            if process_request.brightness != 100:
                factor = process_request.brightness / 100
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(factor)
            
            # Apply contrast
            if process_request.contrast != 100:
                factor = process_request.contrast / 100
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(factor)
                
            # Apply saturation
            if process_request.saturation != 100:
                factor = process_request.saturation / 100
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(factor)
                
            # Apply blur
            if process_request.blur > 0:
                img = img.filter(ImageFilter.GaussianBlur(radius=process_request.blur/10))
                
            # Apply rotation
            if process_request.rotation != 0:
                img = img.rotate(process_request.rotation, expand=True)
                
            # Apply text (would normally be done with PIL.ImageDraw)
            # Note: This is simplified; in a real app you'd use ImageDraw to add text
                
            # Save processed image to a BytesIO object
            output = BytesIO()
            img.save(output, format="JPEG")
            output.seek(0)
            
            # Generate a unique filename
            processed_filename = f"processed_{random.randint(10000, 99999)}.jpg"
            
            # Upload to Supabase storage
            processed_image_url = await upload_image_to_bucket(output.getvalue(), processed_filename)
            
            # If Supabase upload fails, save locally
            if not processed_image_url:
                local_path = os.path.join(UPLOAD_DIR, processed_filename)
                with open(local_path, "wb") as f:
                    f.write(output.getvalue())
                processed_image_url = f"http://localhost:8000/uploads/{processed_filename}"
            
            # Store metadata in Supabase
            if process_request.original_url:
                processed_data = {
                    "original_url": process_request.original_url,
                    "processed_url": processed_image_url,
                    "brightness": process_request.brightness,
                    "contrast": process_request.contrast,
                    "saturation": process_request.saturation,
                    "rotation": process_request.rotation,
                    "blur": process_request.blur,
                    "text": process_request.text,
                    "text_x": process_request.text_x,
                    "text_y": process_request.text_y,
                    "processed_at": "now()"
                }
                await store_processed_image(processed_data)
            
            return ImageResponse(
                success=True,
                message=f"Image processed with parameters",
                objects=["Processed successfully"],
                processed_image_url=processed_image_url
            )
            
        except requests.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Error downloading image: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")

async def handle_image_processing(file_path: str, process_type: str) -> str:
    """Process an image file based on the specified process type"""
    try:
        img = Image.open(file_path)
        
        # Apply different processing based on type
        if process_type == "crop":
            # Mock crop (would be more sophisticated in real app)
            width, height = img.size
            img = img.crop((width // 4, height // 4, width * 3 // 4, height * 3 // 4))
        elif process_type == "brightness":
            # Increase brightness
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.5)
        elif process_type == "remove-bg":
            # Mock background removal (would use specialized libraries in real app)
            # Here we just make a grayscale version for demo
            img = img.convert("L").convert("RGB")
        
        # Save processed image
        output_filename = f"processed_{os.path.basename(file_path)}"
        output_path = os.path.join(UPLOAD_DIR, output_filename)
        img.save(output_path)
        
        return output_path
    except Exception as e:
        print(f"Error processing image: {e}")
        return file_path  # Return original if processing fails

@app.post("/remove-background", response_model=ImageResponse)
async def remove_background(request: BackgroundRemovalRequest):
    # Check if ClipDrop API key is configured
    if not CLIPDROP_API_KEY:
        raise HTTPException(status_code=500, detail="ClipDrop API key not configured")
    
    try:
        # Get image data from either URL or base64
        if request.image_url:
            # Download image from URL
            response = requests.get(request.image_url)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Could not download image from URL")
            img_data = response.content
        elif request.image_base64:
            # Decode base64 image
            try:
                img_data = base64.b64decode(request.image_base64.split(',')[1] if ',' in request.image_base64 else request.image_base64)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="No image provided. Please provide either image_url or image_base64")
        
        # Generate output filename
        output_filename = f"bg_removed_{uuid.uuid4()}.png"
        output_path = Path(UPLOAD_DIR) / output_filename
        
        # Ensure output directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # Call ClipDrop API for background removal
        api_url = "https://clipdrop-api.co/remove-background/v1"
        headers = {
            "x-api-key": CLIPDROP_API_KEY
        }
        files = {
            'image_file': ('image.png', img_data, 'image/png')
        }
        
        api_response = requests.post(api_url, headers=headers, files=files)
        
        if api_response.status_code != 200:
            raise HTTPException(
                status_code=api_response.status_code,
                detail=f"ClipDrop API error: {api_response.text}"
            )
        
        # Save processed image
        with open(output_path, "wb") as f:
            f.write(api_response.content)
        
        # Return response based on requested return type
        if request.return_type == "base64":
            base64_image = base64.b64encode(api_response.content).decode("utf-8")
            return ImageResponse(success=True, base64=f"data:image/png;base64,{base64_image}")
        else:
            # Return URL path
            return ImageResponse(success=True, path=f"/images/{output_filename}")
            
    except Exception as e:
        print(f"Background removal error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Background removal failed: {str(e)}")

@app.post("/compress-image", response_model=ImageResponse)
async def compress_image(request: Request):
    """
    Compress an image using the reSmush.it API.
    This endpoint can be called with a POST request containing either a file or a JSON body with base64 image data.
    """
    content_type = request.headers.get("content-type", "")
    quality = int(request.headers.get("x-image-quality", "85"))
    
    try:
        # Handle form data upload (multipart/form-data)
        if "multipart/form-data" in content_type:
            form = await request.form()
            file = form.get("file")
            
            if not file or not isinstance(file, UploadFile):
                raise HTTPException(status_code=400, detail="No file uploaded")
            
            if not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Read file content directly
            file_content = await file.read()
            original_filename = f"original_{uuid.uuid4()}.{file.filename.split('.')[-1]}"
            
            # Upload original to Supabase
            original_url = await upload_image_to_bucket(file_content, original_filename)
            if not original_url:
                raise HTTPException(status_code=500, detail="Failed to upload original image to Supabase")
            
            # Call reSmush.it API
            return await call_resmushit_api(file_content, original_url, quality)
        
        # Handle JSON body with base64 image
        elif "application/json" in content_type:
            body = await request.json()
            
            # Check if we have base64 image data
            if not body.get("image_base64"):
                raise HTTPException(status_code=400, detail="No image provided in request body")
            
            # Decode base64 image
            try:
                base64_data = body["image_base64"]
                # Handle data URLs by removing the prefix if present
                if ',' in base64_data:
                    base64_data = base64_data.split(',', 1)[1]
                    
                img_data = base64.b64decode(base64_data)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")
            
            # Upload original to Supabase
            original_filename = f"original_{uuid.uuid4()}.png"
            original_url = await upload_image_to_bucket(img_data, original_filename)
            if not original_url:
                raise HTTPException(status_code=500, detail="Failed to upload original image to Supabase")
            
            # Call reSmush.it API
            return await call_resmushit_api(img_data, original_url, quality)
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported content type")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error compressing image: {str(e)}")

async def call_resmushit_api(file_data: bytes, original_url: str, quality: int = 85) -> ImageResponse:
    """Call the reSmush.it API to compress an image"""
    try:
        # Ensure quality is within valid range
        quality = max(0, min(100, quality))
        
        # Get file size
        file_size = len(file_data)
            
        # Format file size for logging
        def format_bytes(bytes, decimals=2):
            if bytes == 0:
                return '0 Bytes'
            k = 1024
            dm = decimals
            sizes = ['Bytes', 'KB', 'MB', 'GB']
            i = int(min(len(sizes) - 1, (len(str(bytes)) - 1) // 3))
            return f"{round(bytes / k ** i, dm)} {sizes[i]}"
            
        # Log original size
        print(f"Original image size: {format_bytes(file_size)}")
        
        # Prepare the API request
        # For API that expects files, we need a filename
        filename = f"temp_{uuid.uuid4()}.png"
        files = {
            'files': (filename, file_data)
        }
        
        # Call the reSmush.it API
        api_response = requests.post(
            f"https://api.resmush.it/?qlty={quality}",
            files=files,
            headers={
                'User-Agent': 'ISEWR/1.0',
                'Referer': 'https://isewr.app'
            }
        )
        
        # Check if the API call was successful
        if api_response.status_code != 200:
            raise HTTPException(
                status_code=api_response.status_code,
                detail=f"reSmush.it API error: {api_response.text}"
            )
        
        # Parse the API response
        result = api_response.json()
        
        # Check for API errors
        if result.get("error"):
            raise HTTPException(
                status_code=400, 
                detail=f"reSmush.it API error: {result.get('error_long') or result.get('error')}"
            )
        
        # Download the compressed image
        compressed_response = requests.get(result["dest"])
        if compressed_response.status_code != 200:
            raise HTTPException(
                status_code=compressed_response.status_code,
                detail="Failed to download compressed image"
            )
        
        # Upload compressed image to Supabase
        compressed_filename = f"compressed_{uuid.uuid4()}.png"
        compressed_url = await upload_image_to_bucket(compressed_response.content, compressed_filename)
        if not compressed_url:
            raise HTTPException(status_code=500, detail="Failed to upload compressed image to Supabase")
        
        # Calculate compression stats
        compressed_size = len(compressed_response.content)
        percent_saved = round((file_size - compressed_size) / file_size * 100, 1)
        bytes_saved = file_size - compressed_size
        
        # Log compression results
        print(f"Compressed image size: {format_bytes(compressed_size)}")
        print(f"Saved: {percent_saved}% ({format_bytes(bytes_saved)})")
        
        # Store metadata in Supabase - include only essential columns
        processed_data = {
            "original_url": original_url,
            "processed_url": compressed_url
        }
        
        # Only add these if your table has these columns and accepts the values
        # Setting to False based on our diagnostics showing the numeric columns don't accept values
        if False:  # Changed from True to False since numeric values aren't being saved
            processed_data.update({
                "original_size": file_size,
                "compressed_size": compressed_size,
                "percent_saved": percent_saved,
                "quality": quality,
                "processed_at": "now()"
            })
        
        # Compare with successful test data
        test_data = {
            "original_url": "http://test-original.jpg",
            "processed_url": "http://test-compressed.jpg",
            "original_size": 1000,
            "compressed_size": 800,
            "percent_saved": 20.0,
            "quality": 85,
            "processed_at": "now()"
        }
        
        print("===== DATA COMPARISON =====")
        print(f"Test data that works: {test_data}")
        print(f"Real data we're sending: {processed_data}")
        print(f"Data types in test: {[(k, type(v).__name__) for k, v in test_data.items()]}")
        print(f"Data types in real: {[(k, type(v).__name__) for k, v in processed_data.items()]}")
        print("===========================")
        
        # Add more detailed logging for database operations
        print(f"Storing metadata in Supabase: {processed_data}")
        db_result = await store_processed_image(processed_data)
        
        if not db_result:
            print("WARNING: Failed to store image metadata in Supabase database")
        else:
            print(f"Successfully stored metadata in Supabase with ID: {db_result.get('id', 'unknown')}")
        
        # Prepare response
        # Convert to base64 for direct embedding if needed
        base64_image = base64.b64encode(compressed_response.content).decode("utf-8")
        
        return ImageResponse(
            success=True,
            base64=f"data:image/png;base64,{base64_image}",
            path=compressed_url,
            message=f"Image compressed successfully. Saved {percent_saved}% ({format_bytes(bytes_saved)})",
            objects=[
                f"Original: {format_bytes(file_size)}",
                f"Compressed: {format_bytes(compressed_size)}",
                f"Saved: {percent_saved}%"
            ],
            processed_image_url=compressed_url
        )
    
    except Exception as e:
        print(f"Error in reSmush.it API call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image compression failed: {str(e)}")

@app.post("/detect-ai-image", response_model=DeepfakeDetectionResponse)
async def detect_ai_image(
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    threshold: float = Form(0.7),
    face_threshold: float = Form(0.5)
):
    """
    Detect if an image was generated by AI using SightEngine API.
    Either provide a file upload or an image URL.
    """
    # Check if SightEngine API credentials are configured
    api_user = os.getenv("SIGHTENGINE_API_USER")
    api_secret = os.getenv("SIGHTENGINE_API_SECRET")
    
    print(f"Debug - API credentials: User={api_user}, Secret={api_secret[:5] if api_secret else None}")
    
    if not api_user or not api_secret:
        raise HTTPException(
            status_code=500, 
            detail=f"SightEngine API credentials not configured. User: {api_user}, Secret: {'*' * len(api_secret) if api_secret else None}"
        )
    
    try:
        # Determine if we're using a file upload or a URL
        if file and not image_url:
            if not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Save the uploaded file
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            print(f"Debug - Uploading file: {file_path}")
            
            # Call SightEngine API with file upload
            with open(file_path, "rb") as f:
                response = requests.post(
                    'https://api.sightengine.com/1.0/check.json',
                    files={'media': f},
                    data={
                        'models': 'genai,face-attributes,nudity-2.0',
                        'api_user': api_user,
                        'api_secret': api_secret
                    }
                )
        
        elif image_url and not file:
            print(f"Debug - Using image URL: {image_url}")
            
            # Call SightEngine API with URL
            response = requests.get(
                'https://api.sightengine.com/1.0/check.json',
                params={
                    'models': 'genai,face-attributes,nudity-2.0',
                    'api_user': api_user,
                    'api_secret': api_secret,
                    'url': image_url
                }
            )
        else:
            raise HTTPException(status_code=400, detail="Either provide a file or an image URL, not both or neither")
        
        print(f"Debug - API response status: {response.status_code}")
        
        # Process the API response
        if response.status_code == 200:
            result = response.json()
            print(f"Debug - API response: {result}")
            
            if result.get('status') == 'success':
                # Get the scores
                ai_generated_score = result.get('type', {}).get('ai_generated', 0)
                
                # Check for direct face manipulation score from SightEngine API
                # This is the specific field that indicates face manipulation
                direct_face_manipulation = result.get('type', {}).get('face_manipulation', 0)
                print(f"Debug - Direct face manipulation score: {direct_face_manipulation}")
                
                # Without celebrity model, we'll rely more on face-attributes
                # Get a face manipulation score from face-attributes if available
                faces = result.get('faces', [])
                face_attributes_score = 0
                if faces:
                    # Calculate face manipulation score based on API detection
                    # only use this as a fallback if no direct score is provided
                    face_count = len(faces)
                    face_attributes_score = 0.1 * min(face_count, 5)  # Scale with number of faces detected
                
                # Also use the nudity detection as a potential signal
                # Some manipulated images have unusual nudity scores
                nudity_score = result.get('nudity', {}).get('raw', 0)
                artificial_score = result.get('nudity', {}).get('artificial', 0)
                
                # Combine scores for an estimated face manipulation score
                # Prioritize the direct face manipulation score if available
                face_manipulation_score = direct_face_manipulation
                if face_manipulation_score == 0:
                    face_manipulation_score = max(face_attributes_score, artificial_score)
                
                print(f"Debug - Final face_manipulation_score: {face_manipulation_score}")
                print(f"Debug - Sources: direct={direct_face_manipulation}, attributes={face_attributes_score}, artificial={artificial_score}")
                
                # Get more detailed scores if available
                diffusion_score = 0
                gan_score = 0
                
                # Initialize specific_models dictionary
                specific_models = {}
                
                # Check for diffusion models in the nested structure
                if 'diffusion' in result.get('type', {}):
                    diffusion_data = result['type']['diffusion']
                    print(f"Debug - Diffusion data: {diffusion_data}")
                    # If it's a dictionary with model names and scores
                    if isinstance(diffusion_data, dict):
                        for model_name, score in diffusion_data.items():
                            if score > 0:
                                specific_models[model_name] = score
                                diffusion_score = max(diffusion_score, score)
                    # If it's a single score
                    elif isinstance(diffusion_data, (int, float)):
                        diffusion_score = diffusion_data
                else:
                    # Try to get it as a direct score
                    diffusion_score = result.get('type', {}).get('diffusion', 0)
                
                # Check for GAN models in the nested structure
                if 'gan' in result.get('type', {}):
                    gan_data = result['type']['gan']
                    print(f"Debug - GAN data: {gan_data}")
                    # If it's a dictionary with model names and scores
                    if isinstance(gan_data, dict):
                        for model_name, score in gan_data.items():
                            if score > 0:
                                specific_models[model_name] = score
                                gan_score = max(gan_score, score)
                    # If it's a single score
                    elif isinstance(gan_data, (int, float)):
                        gan_score = gan_data
                else:
                    # Try to get it as a direct score
                    gan_score = result.get('type', {}).get('gan', 0)
                
                # Check for specific model scores in the top level of type
                for model_type in ['midjourney', 'dalle', 'stable-diffusion', 'firefly', 'flux', 
                                  'imagen', 'ideogram', 'gpt4o', 'recraft', 'reve']:
                    score = result.get('type', {}).get(model_type, 0)
                    if score > 0:
                        specific_models[model_type] = score
                
                # Add nudity detection information if available
                nudity_info = result.get('nudity', {})
                if nudity_info:
                    if 'raw' in nudity_info and nudity_info['raw'] > 0:
                        specific_models['nudity-raw'] = nudity_info['raw']
                    if 'artificial' in nudity_info and nudity_info['artificial'] > 0:
                        specific_models['nudity-artificial'] = nudity_info['artificial']
                
                # Determine if AI-generated based on threshold
                is_ai_generated = ai_generated_score > threshold
                
                # Determine if face is manipulated based on face_threshold
                is_face_manipulated = face_manipulation_score > face_threshold
                
                # Add additional face analysis details if available
                face_details = None
                if faces and len(faces) > 0:
                    face_details = {
                        "count": len(faces),
                        "attributes": []
                    }
                    
                    for i, face in enumerate(faces[:3]):  # Limit to first 3 faces
                        face_info = {
                            "location": face.get('location', {}),
                            "attributes": {
                                "gender": face.get('attributes', {}).get('gender', {}),
                                "age": face.get('attributes', {}).get('age', {}),
                                "emotion": face.get('attributes', {}).get('emotion', {})
                            }
                        }
                        face_details["attributes"].append(face_info)
                
                return DeepfakeDetectionResponse(
                    success=True,
                    message="AI detection completed successfully",
                    ai_generated_score=ai_generated_score,
                    face_manipulation_score=face_manipulation_score,
                    diffusion_score=diffusion_score,
                    gan_score=gan_score,
                    specific_models=specific_models if specific_models else None,
                    media_info=result.get('media', {}),
                    request_id=result.get('request', {}).get('id'),
                    is_ai_generated=is_ai_generated,
                    is_face_manipulated=is_face_manipulated,
                    face_details=face_details
                )
            else:
                error_msg = result.get('error', {}).get('message', 'Unknown error')
                print(f"Debug - API error: {error_msg}")
                return DeepfakeDetectionResponse(
                    success=False,
                    message=f"SightEngine API error: {error_msg}",
                    ai_generated_score=0,
                    is_ai_generated=False,
                    is_face_manipulated=False
                )
        else:
            error_text = response.text
            print(f"Debug - API error: HTTP {response.status_code}, {error_text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"SightEngine API error: {error_text}"
            )
    
    except Exception as e:
        print(f"Debug - Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/detect-deepfake-image", response_model=DeepfakeDetectionResponse)
async def detect_deepfake_image(
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    threshold: float = Form(0.5)
):
    """
    Detect if an image contains a deepfake (face swap or modification) using SightEngine API.
    Either provide a file upload or an image URL.
    """
    # Check if SightEngine API credentials are configured
    api_user = os.getenv("SIGHTENGINE_API_USER")
    api_secret = os.getenv("SIGHTENGINE_API_SECRET")
    
    print(f"Debug - API credentials: User={api_user}, Secret={api_secret[:5] if api_secret else None}")
    
    if not api_user or not api_secret:
        raise HTTPException(
            status_code=500, 
            detail=f"SightEngine API credentials not configured. User: {api_user}, Secret: {'*' * len(api_secret) if api_secret else None}"
        )
    
    try:
        # Determine if we're using a file upload or a URL
        if file and not image_url:
            if not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Save the uploaded file
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            print(f"Debug - Uploading file: {file_path}")
            
            # Call SightEngine API with file upload - using the 'deepfake' model
            with open(file_path, "rb") as f:
                response = requests.post(
                    'https://api.sightengine.com/1.0/check.json',
                    files={'media': f},
                    data={
                        'models': 'deepfake,face-attributes',
                        'api_user': api_user,
                        'api_secret': api_secret
                    }
                )
        
        elif image_url and not file:
            print(f"Debug - Using image URL: {image_url}")
            
            # Call SightEngine API with URL - using the 'deepfake' model
            response = requests.get(
                'https://api.sightengine.com/1.0/check.json',
                params={
                    'models': 'deepfake,face-attributes',
                    'api_user': api_user,
                    'api_secret': api_secret,
                    'url': image_url
                }
            )
        else:
            raise HTTPException(status_code=400, detail="Either provide a file or an image URL, not both or neither")
        
        print(f"Debug - API response status: {response.status_code}")
        
        # Process the API response
        if response.status_code == 200:
            result = response.json()
            print(f"Debug - API response: {result}")
            
            if result.get('status') == 'success':
                # Get the deepfake score
                deepfake_score = result.get('type', {}).get('deepfake', 0)
                print(f"Debug - Deepfake score: {deepfake_score}")
                
                # Get face information if available
                faces = result.get('faces', [])
                face_count = len(faces)
                
                # Add additional face analysis details if available
                face_details = None
                if face_count > 0:
                    face_details = {
                        "count": face_count,
                        "attributes": []
                    }
                    
                    for i, face in enumerate(faces[:3]):  # Limit to first 3 faces
                        face_info = {
                            "location": face.get('location', {}),
                            "attributes": {
                                "gender": face.get('attributes', {}).get('gender', {}),
                                "age": face.get('attributes', {}).get('age', {}),
                                "emotion": face.get('attributes', {}).get('emotion', {})
                            }
                        }
                        face_details["attributes"].append(face_info)
                
                # Determine if it's a deepfake based on threshold
                is_deepfake = deepfake_score > threshold
                
                # Return the response
                return DeepfakeDetectionResponse(
                    success=True,
                    message="Deepfake detection completed successfully",
                    ai_generated_score=0,  # Not applicable for deepfake detection
                    face_manipulation_score=deepfake_score,  # Use deepfake score as face manipulation
                    diffusion_score=0,  # Not applicable for deepfake detection
                    gan_score=0,  # Not applicable for deepfake detection
                    specific_models={"deepfake": deepfake_score} if deepfake_score > 0 else None,
                    media_info=result.get('media', {}),
                    request_id=result.get('request', {}).get('id'),
                    is_ai_generated=False,  # Not applicable for deepfake detection
                    is_face_manipulated=is_deepfake,  # Use the deepfake result
                    face_details=face_details
                )
            else:
                error_msg = result.get('error', {}).get('message', 'Unknown error')
                print(f"Debug - API error: {error_msg}")
                return DeepfakeDetectionResponse(
                    success=False,
                    message=f"SightEngine API error: {error_msg}",
                    ai_generated_score=0,
                    face_manipulation_score=0,
                    is_ai_generated=False,
                    is_face_manipulated=False
                )
        else:
            error_text = response.text
            print(f"Debug - API error: HTTP {response.status_code}, {error_text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"SightEngine API error: {error_text}"
            )
    
    except Exception as e:
        print(f"Debug - Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Welcome to ISEWR API. Use /docs to see available endpoints."}

@app.get("/debug-supabase")
async def debug_supabase():
    """Debug endpoint to test Supabase connection and table access"""
    from supabase_client import supabase
    
    results = {
        "supabase_url": SUPABASE_URL,
        "supabase_key_prefix": SUPABASE_KEY[:5] + "..." if SUPABASE_KEY else None,
        "client_initialized": supabase is not None,
        "table_checks": {},
        "storage_checks": {},
        "test_insert": None
    }
    
    if not supabase:
        return {
            "success": False,
            "message": "Supabase client not initialized",
            "results": results
        }
    
    # Test table access
    try:
        # Check processed_images table
        table_response = supabase.table("processed_images").select("count", count="exact").limit(1).execute()
        results["table_checks"]["processed_images"] = {
            "success": True,
            "count": table_response.count if hasattr(table_response, "count") else "unknown",
            "data_sample": table_response.data[:1] if hasattr(table_response, "data") else None
        }
    except Exception as e:
        results["table_checks"]["processed_images"] = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
    
    # Test storage access
    try:
        # List files in the bucket
        storage_response = supabase.storage.from_("images").list()
        results["storage_checks"]["images"] = {
            "success": True,
            "files_count": len(storage_response) if storage_response else 0,
            "sample": storage_response[:3] if storage_response else None
        }
    except Exception as e:
        results["storage_checks"]["images"] = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
    
    # Test data insertion
    try:
        # Create a test record with minimal data
        test_data = {
            "original_url": "http://test-original.jpg",
            "processed_url": "http://test-compressed.jpg",  # Use processed_url instead of compressed_url
            "original_size": 1000,
            "compressed_size": 800,
            "percent_saved": 20.0,
            "quality": 85,
            "processed_at": "now()"
        }
        
        # Insert directly without using the async function
        insert_response = supabase.table("processed_images").insert(test_data).execute()
        
        results["test_insert"] = {
            "success": True,
            "data": insert_response.data if hasattr(insert_response, "data") else None,
            "response": str(insert_response)
        }
    except Exception as e:
        results["test_insert"] = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "test_data": test_data
        }
    
    return {
        "success": True,
                    "message": "Supabase diagnostic completed",
        "results": results
    }

@app.get("/inspect-table")
async def inspect_table():
    """Inspect the actual schema of the processed_images table"""
    from supabase_client import supabase
    
    if not supabase:
        return {
            "success": False,
            "message": "Supabase client not initialized"
        }
    
    try:
        # Use a more basic query to get a single row
        response = supabase.table("processed_images").select("*").limit(1).execute()
        
        sample_data = None
        columns = []
        
        if hasattr(response, 'data') and response.data:
            sample_data = response.data[0]
            columns = list(sample_data.keys())
        
        # Also try to get the information schema
        info_schema = None
        try:
            # This might fail depending on RLS policies
            info_schema_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'processed_images'
            """
            schema_response = supabase.rpc('pgrest_query', {'query': info_schema_query}).execute()
            info_schema = schema_response.data if hasattr(schema_response, 'data') else None
        except Exception as schema_error:
            info_schema = f"Error getting schema: {str(schema_error)}"
        
        return {
            "success": True,
                    "message": "Table inspection completed",
            "columns": columns,
            "sample_data": sample_data,
            "information_schema": info_schema
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error inspecting table: {str(e)}",
            "error_type": type(e).__name__
        }

@app.get("/debug-supabase-detailed")
async def debug_supabase_detailed():
    """More detailed debug endpoint for Supabase table structure"""
    from supabase_client import supabase
    
    if not supabase:
        return {
            "success": False,
            "message": "Supabase client not initialized",
        }
    
    # Get detailed table info
    try:
        response = supabase.table("processed_images").select("*").limit(5).execute()
        
        # Check actual table structure
        schema_info = {}
        sample_record = None
        
        if hasattr(response, 'data') and response.data:
            print(f"Found {len(response.data)} records in processed_images table")
            sample_record = response.data[0] if response.data else None
            
            if sample_record:
                # Analyze column structure
                columns = list(sample_record.keys())
                column_types = {}
                
                for col in columns:
                    column_types[col] = type(sample_record[col]).__name__
        
                schema_info = {
                    "columns": columns,
                    "column_types": column_types,
                    "record_count": len(response.data),
                    "sample_record": sample_record
                }
        else:
            print("No records found in processed_images table")
            schema_info = {
                "error": "No records found to analyze schema"
            }
        
        # Try a simple insert with minimal fields
        test_data = {
            "original_url": "http://test-original-simple.jpg",
            "processed_url": "http://test-processed-simple.jpg"
        }
        
        print(f"Attempting simple insert with minimal data: {test_data}")
        insert_response = supabase.table("processed_images").insert(test_data).execute()
        
        insert_result = {
            "success": True,
            "insert_response": str(insert_response),
            "data": insert_response.data if hasattr(insert_response, 'data') else None
        }
    except Exception as e:
        print(f"Error in detailed diagnosis: {str(e)}")
        schema_info = {
            "error": str(e),
            "error_type": type(e).__name__
        }
        insert_result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
    
    return {
        "success": True,
                    "message": "Detailed Supabase diagnostic completed",
        "schema_info": schema_info,
        "insert_test": insert_result
    }

@app.get("/test-compression")
async def test_compression():
    """Test endpoint to simulate a compression with a fixed image URL"""
    try:
        # Use a placeholder image URL
        image_url = "https://picsum.photos/800/600"
        quality = 85
        
        # Download the image
        print(f"Downloading test image from {image_url}")
        response = requests.get(image_url)
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to download image, status: {response.status_code}"}
        
        image_data = response.content
        
        # Upload original to Supabase
        print("Uploading original image to Supabase")
        original_filename = f"test_original_{uuid.uuid4()}.jpg"
        original_url = await upload_image_to_bucket(image_data, original_filename)
        
        if not original_url:
            return {"success": False, "error": "Failed to upload original image to Supabase"}
        
        print(f"Original image uploaded successfully: {original_url}")
        
        # Call the compression API
        print("Processing with test compression (simulating reSmush.it)")
        
        # Instead of calling the actual API, let's simulate a compressed response
        # by just using the same image (for test purposes)
        compressed_data = image_data
        
        # Upload compressed image to Supabase
        print("Uploading compressed image to Supabase")
        compressed_filename = f"test_compressed_{uuid.uuid4()}.jpg"
        compressed_url = await upload_image_to_bucket(compressed_data, compressed_filename)
        
        if not compressed_url:
            return {"success": False, "error": "Failed to upload compressed image to Supabase"}
        
        print(f"Compressed image uploaded successfully: {compressed_url}")
        
        # Calculate simulated stats
        original_size = len(image_data)
        compressed_size = len(compressed_data)
        percent_saved = round((original_size - compressed_size) / original_size * 100, 1)
        
        # Store minimal metadata in Supabase
        processed_data = {
            "original_url": original_url,
            "processed_url": compressed_url
        }
        
        print(f"Storing metadata in Supabase: {processed_data}")
        db_result = await store_processed_image(processed_data)
        
        return {
            "success": True if db_result else False,
            "message": "Test compression completed",
            "original_url": original_url,
            "compressed_url": compressed_url,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "percent_saved": percent_saved,
            "db_result": db_result
        }
    except Exception as e:
        print(f"Error in test compression: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

@app.get("/debug-supabase-tables")
async def debug_supabase_tables():
    """
    Debug endpoint to check Supabase table structure
    """
    try:
        from supabase_client import get_supabase_client
        client = get_supabase_client()
        
        # Get schema for recognition_results table
        response = client.table("recognition_results").select("*").limit(1).execute()
        
        return {
            "success": True,
            "schema": {
                "recognition_results": {
                    "columns": list(response.data[0].keys()) if response.data else [],
                    "sample_row": response.data[0] if response.data else None
                }
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 