import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API credentials
api_user = os.getenv("SIGHTENGINE_API_USER")
api_secret = os.getenv("SIGHTENGINE_API_SECRET")

if not api_user or not api_secret:
    print("Error: SightEngine API credentials not found in environment variables")
    exit(1)

print(f"Using SightEngine API credentials: User={api_user}, Secret={api_secret[:5]}...")

# Test image URLs - using public images
test_images = {
    "natural": "https://upload.wikimedia.org/wikipedia/commons/c/c4/PM_Modi_2015.jpg",  # Natural photo
    "ai_generated": "https://static.wikia.nocookie.net/aigc/images/4/45/MidjourneyExample.png"  # AI-generated image
}

# Define models to test
models_to_test = [
    'genai',               # AI image detection
    'nudity-2.0',          # Nudity detection
    'face-attributes',     # Face detection and attributes
    'text',                # Text detection
    'offensive',           # Offensive content detection
    'wad'                  # Weapons, alcohol, drugs
]

# Define combinations to test
test_cases = [
    {"model": "genai", "params": {}},
    {"model": "face-attributes", "params": {}},
    {"model": "genai,face-attributes", "params": {}}
]

def call_sightengine_api(image_url, models, extra_params=None):
    """Call the SightEngine API with specified models and parameters"""
    params = {
        'models': models,
        'api_user': api_user,
        'api_secret': api_secret,
        'url': image_url
    }
    
    if extra_params:
        params.update(extra_params)
    
    print(f"Calling API with URL: {image_url}")
    response = requests.get(
        'https://api.sightengine.com/1.0/check.json',
        params=params
    )
    
    return response

def print_response_details(response, image_type, models):
    """Print details from the API response"""
    print(f"\n{'='*80}")
    print(f"TESTING: {image_type.upper()} IMAGE WITH MODELS: {models}")
    print(f"{'='*80}")
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    
    if result.get('status') != 'success':
        print(f"API Error: {result}")
        return
    
    # Print all keys in the response
    print(f"Response keys: {list(result.keys())}")
    
    # Handle specific model responses
    if 'type' in result:
        print("\nGENAI RESULTS:")
        print(f"AI Generated Score: {result['type'].get('ai_generated', 0)}")
        
        # Check for diffusion models
        if 'diffusion' in result['type']:
            print("\nDiffusion Models:")
            for model, score in result['type']['diffusion'].items():
                print(f"- {model}: {score}")
        
        # Check for GAN models
        if 'gan' in result['type']:
            print("\nGAN Models:")
            for model, score in result['type']['gan'].items():
                print(f"- {model}: {score}")
                
        # Check for manipulation
        if 'face_manipulation' in result['type']:
            print(f"\nFace Manipulation Score: {result['type']['face_manipulation']}")
    
    # Handle face attributes
    if 'faces' in result:
        print(f"\nFACE ATTRIBUTES:")
        print(f"Number of faces detected: {len(result['faces'])}")
        for i, face in enumerate(result['faces']):
            print(f"\nFace #{i+1}:")
            if 'attributes' in face:
                print(f"- Attributes: {json.dumps(face.get('attributes', {}), indent=2)}")
            if 'celebrity' in face:
                for celeb in face.get('celebrity', {}).get('matches', []):
                    print(f"- Celebrity match: {celeb.get('name')} ({celeb.get('score'):.2f})")
    
    # Handle nudity detection
    if 'nudity' in result:
        print("\nNUDITY DETECTION:")
        print(json.dumps(result['nudity'], indent=2))
    
    # Handle other models
    for model in ['text', 'offensive', 'wad']:
        if model in result:
            print(f"\n{model.upper()} DETECTION:")
            print(json.dumps(result[model], indent=2))

# Run tests
for image_type, image_url in test_images.items():
    for test_case in test_cases:
        try:
            response = call_sightengine_api(
                image_url, 
                test_case["model"], 
                test_case["params"]
            )
            print_response_details(response, image_type, test_case["model"])
        except Exception as e:
            print(f"Exception: {str(e)}")

print("\nDone testing models") 