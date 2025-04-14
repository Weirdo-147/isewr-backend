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

# Test with a sample image URL - using SightEngine's example image
test_image_url = "https://sightengine.com/assets/img/examples/example-fac-1000.jpg"

# Call SightEngine API with URL - using the 'deepfake' model
print(f"Testing deepfake detection with URL: {test_image_url}")
response = requests.get(
    'https://api.sightengine.com/1.0/check.json',
    params={
        'models': 'deepfake',
        'api_user': api_user,
        'api_secret': api_secret,
        'url': test_image_url
    }
)

# Print response
print(f"Status code: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    if result.get('status') == 'success':
        print("\nFULL RESPONSE DATA:")
        print(json.dumps(result, indent=2))
        
        # Print deepfake score
        deepfake_score = result.get('type', {}).get('deepfake', 0)
        print(f"\nDeepfake Score: {deepfake_score}")
        
        # Interpret the score
        if deepfake_score < 0.3:
            interpretation = "Likely authentic (not deepfake)"
        elif deepfake_score < 0.7:
            interpretation = "Uncertain - might be a deepfake"
        else:
            interpretation = "Likely deepfake"
            
        print(f"Interpretation: {interpretation}")
        
    else:
        print(f"API Error: {result}")
else:
    print(f"API call failed: {response.text}")

# Optional: If you have a local test file, test with file upload too
test_file_path = "test_images/deepfake_test.jpg"
if os.path.exists(test_file_path):
    print(f"\nTesting with local file: {test_file_path}")
    
    with open(test_file_path, "rb") as f:
        file_response = requests.post(
            'https://api.sightengine.com/1.0/check.json',
            files={'media': f},
            data={
                'models': 'deepfake',
                'api_user': api_user,
                'api_secret': api_secret
            }
        )
    
    print(f"File upload status code: {file_response.status_code}")
    
    if file_response.status_code == 200:
        file_result = file_response.json()
        if file_result.get('status') == 'success':
            deepfake_score = file_result.get('type', {}).get('deepfake', 0)
            print(f"File Deepfake Score: {deepfake_score}")
        else:
            print(f"API Error with file upload: {file_result}")
    else:
        print(f"File API call failed: {file_response.text}")
else:
    print(f"\nSkipping file upload test (file not found: {test_file_path})")
    print("To test with a file, place a test image at the path above") 