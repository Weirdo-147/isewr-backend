from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ImageResponse(BaseModel):
    success: bool
    message: str
    objects: List[str]
    processed_image_url: Optional[str] = None

class ProcessRequest(BaseModel):
    image_url: str
    original_url: Optional[str] = None
    brightness: Optional[int] = 100
    contrast: Optional[int] = 100
    saturation: Optional[int] = 100
    rotation: Optional[int] = 0
    blur: Optional[int] = 0
    text: Optional[str] = None
    text_x: Optional[float] = None
    text_y: Optional[float] = None
    text_size: Optional[int] = 24
    text_color: Optional[str] = "#000000"
    filter: Optional[str] = "none"

class BackgroundRemovalRequest(BaseModel):
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    return_type: str = "url"  # Can be "url" or "base64"
    transparency_handling: Optional[str] = "return_input_if_non_opaque"

class VideoConversionRequest(BaseModel):
    image_url: Optional[str] = None
    prompt: str
    style: str = "kling-1.0-pro"
    aspect_ratio: str = "1:1"
    status: Optional[str] = "pending"

class VideoConversionResponse(BaseModel):
    id: str
    status: str
    video_url: Optional[str] = None
    created_at: Optional[str] = None

class SupabaseConfig(BaseModel):
    url: str
    key: str

# SightEngine AI Detection Models
class DeepfakeDetectionRequest(BaseModel):
    url: Optional[str] = None
    image_file: Optional[bytes] = None
    return_type: str = "json"

class DeepfakeDetectionResponse(BaseModel):
    success: bool
    message: str
    ai_generated_score: float
    face_manipulation_score: Optional[float] = None
    diffusion_score: Optional[float] = None
    gan_score: Optional[float] = None
    specific_models: Optional[Dict[str, float]] = None
    media_info: Optional[dict] = None
    request_id: Optional[str] = None
    is_ai_generated: bool = False
    is_face_manipulated: bool = False
    face_details: Optional[Dict[str, Any]] = None 