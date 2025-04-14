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

# Test with a local image file that may have face manipulation
test_file_path = "test_images/face_manipulation_test.jpg"

if not os.path.exists(test_file_path):
    print(f"Error: Test file not found at {test_file_path}")
    print("Please place a test image in the test_images directory")
    # Create directory if it doesn't exist
    os.makedirs("test_images", exist_ok=True)
    exit(1)

# Call SightEngine API with file upload
with open(test_file_path, "rb") as f:
    response = requests.post(
        'https://api.sightengine.com/1.0/check.json',
        files={'media': f},
        data={
            'models': 'genai,face-attributes,nudity-2.0',
            'api_user': api_user,
            'api_secret': api_secret
        }
    )

# Print response
print(f"Status code: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    if result.get('status') == 'success':
        print("\nALL RESPONSE DATA:")
        print(json.dumps(result, indent=2))
        
        # Print face manipulation specific data
        face_manipulation = result.get('type', {}).get('face_manipulation', 0)
        print(f"\nFace Manipulation Score: {face_manipulation}")
        
        # Print AI generation data
        ai_generated = result.get('type', {}).get('ai_generated', 0)
        print(f"AI Generated Score: {ai_generated}")
        
        # Calculate fallback face manipulation score for comparison
        faces = result.get('faces', [])
        face_attributes_score = 0
        if faces:
            face_count = len(faces)
            face_attributes_score = 0.1 * min(face_count, 5)
        artificial_score = result.get('nudity', {}).get('artificial', 0)
        fallback_score = max(face_attributes_score, artificial_score)
        
        print(f"\nFace Manipulation Score Breakdown:")
        print(f"- Direct API score: {face_manipulation}")
        print(f"- Fallback calculation: {fallback_score}")
        print(f"  - From face attributes: {face_attributes_score} (based on {len(faces)} faces)")
        print(f"  - From artificial nudity: {artificial_score}")
        print(f"- Score that would be used: {face_manipulation or fallback_score}")
        
        # Check for diffusion models
        if 'diffusion' in result.get('type', {}):
            diffusion_data = result['type']['diffusion']
            print(f"\nDiffusion data: {diffusion_data}")
            
            if isinstance(diffusion_data, dict):
                print("\nDiffusion Models:")
                for model, score in diffusion_data.items():
                    print(f"- {model}: {score}")
        
        # Check for GAN models
        if 'gan' in result.get('type', {}):
            gan_data = result['type']['gan']
            print(f"\nGAN data: {gan_data}")
            
            if isinstance(gan_data, dict):
                print("\nGAN Models:")
                for model, score in gan_data.items():
                    print(f"- {model}: {score}")
        
        # Check for faces
        faces = result.get('faces', [])
        if faces:
            print(f"\nNumber of faces detected: {len(faces)}")
            for i, face in enumerate(faces):
                print(f"\nFace #{i+1}:")
                if 'attributes' in face:
                    print(f"- Attributes: {json.dumps(face.get('attributes', {}), indent=2)}")
    else:
        print(f"API Error: {result}")
else:
    print(f"API call failed: {response.text}") 