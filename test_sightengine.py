from dotenv import load_dotenv
import os
import requests

load_dotenv()

# Get SightEngine API credentials
api_user = os.getenv("SIGHTENGINE_API_USER")
api_secret = os.getenv("SIGHTENGINE_API_SECRET")

print(f"Using API credentials: User={api_user}, Secret={api_secret[:5]}...")

# Test image URL
test_image_url = "https://sightengine.com/assets/img/examples/example-prop-c1.jpg"

# Call SightEngine API
response = requests.get(
    'https://api.sightengine.com/1.0/check.json',
    params={
        'models': 'genai',
        'api_user': api_user,
        'api_secret': api_secret,
        'url': test_image_url
    }
)

# Print response
print(f"Status code: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    result = response.json()
    if result.get('status') == 'success':
        ai_generated_score = result.get('type', {}).get('ai_generated', 0)
        print(f"AI Generated Score: {ai_generated_score}")
    else:
        print(f"API Error: {result}")
else:
    print("API call failed") 