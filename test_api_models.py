import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Get SightEngine API credentials
api_user = os.getenv("SIGHTENGINE_API_USER")
api_secret = os.getenv("SIGHTENGINE_API_SECRET")

print(f"Using SightEngine API credentials: User={api_user}, Secret={api_secret[:5]}...")

# Test image URL
test_image_url = "https://sightengine.com/assets/img/examples/example-prop-c1.jpg"

# Test with different models to check what's available
models_to_test = [
    'genai',
    'celebrity',
    'face-attributes',
    'nudity-2.0',
    'standard'
]

for model in models_to_test:
    print(f"\nTesting model: {model}")
    
    # Call SightEngine API with URL
    try:
        response = requests.get(
            'https://api.sightengine.com/1.0/check.json',
            params={
                'models': model,
                'api_user': api_user,
                'api_secret': api_secret,
                'url': test_image_url
            }
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response keys: {list(result.keys())}")
            
            if 'status' in result and result['status'] == 'success':
                # Print available sections of the response based on the model
                if model == 'genai' and 'type' in result:
                    print(f"AI generation score: {result['type'].get('ai_generated', 0)}")
                elif model == 'celebrity' and 'celebrity' in result:
                    print(f"Celebrity score: {result['celebrity'].get('celebrity', 0)}")
                    if 'matches' in result['celebrity'] and result['celebrity']['matches']:
                        print(f"Top match: {result['celebrity']['matches'][0].get('name')} - {result['celebrity']['matches'][0].get('score')}")
                elif model == 'face-attributes' and 'faces' in result:
                    print(f"Number of faces: {len(result.get('faces', []))}")
                    if result.get('faces'):
                        face = result['faces'][0]
                        print(f"Face attributes: {face.get('attributes', {})}")
                        
            else:
                print(f"Error: {result.get('error', {})}")
        else:
            print(f"Error: {response.text}")
                
    except Exception as e:
        print(f"Exception: {str(e)}")
        
print("\nDone testing models") 