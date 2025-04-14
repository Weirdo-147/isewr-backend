from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HelloResponse(BaseModel):
    message: str

@app.get("/", response_model=HelloResponse)
async def root():
    return HelloResponse(message="Hello world! Backend is running.")

class RecognitionRequest(BaseModel):
    image_url: str

class RecognitionResponse(BaseModel):
    success: bool
    message: str
    objects: List[str] = []

@app.post("/recognize", response_model=RecognitionResponse)
async def recognize_image(request: RecognitionRequest):
    # Mock response for testing
    return RecognitionResponse(
        success=True,
        message="Mock recognition successful",
        objects=["Person", "Car", "Building"]
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_simple:app", host="0.0.0.0", port=8000, reload=True) 