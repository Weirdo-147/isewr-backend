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

# Use a single known working image
image_url = "https://img-cdn.inc.com/image/upload/w_1920,h_1080,c_fill/images/panoramic/gettyimages-1229892421_513443_mgizkp.jpg"

# Call SightEngine API
params = {
    'models': 'genai',
    'api_user': api_user,
    'api_secret': api_secret,
    'url': image_url
}

print(f"Calling API with URL: {image_url}")
response = requests.get('https://api.sightengine.com/1.0/check.json', params=params)

# Print response
print(f"Status code: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    result = response.json()
    if result.get('status') == 'success':
        print("\nALL RESPONSE DATA:")
        print(json.dumps(result, indent=2))
        
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
    else:
        print(f"API Error: {result}")
else:
    print("API call failed") 