import requests

# Test image URL to use
image_url = "https://sightengine.com/assets/img/examples/example-prop-c1.jpg"

# Test the endpoint
print(f"Testing /detect-ai-image endpoint with URL: {image_url}")

try:
    response = requests.post(
        "http://localhost:8000/detect-ai-image",
        data={"image_url": image_url}
    )
    
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("Endpoint test successful!")
    else:
        print(f"Endpoint test failed with status code {response.status_code}")
        
except Exception as e:
    print(f"Error testing endpoint: {str(e)}") 