import requests
import json

# Test image URL
test_image_url = "https://sightengine.com/assets/img/examples/example-prop-c1.jpg"

print(f"Testing with URL: {test_image_url}")

# Create form data exactly like the frontend would
form_data = {
    'image_url': test_image_url,
    'threshold': 0.7,
    'face_threshold': 0.5
}

try:
    # Add more debugging information
    print(f"Sending request to: http://localhost:8000/detect-ai-image")
    print(f"With data: {form_data}")
    
    # Send the request
    response = requests.post(
        'http://localhost:8000/detect-ai-image',
        data=form_data  # Use data instead of params for form data
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.text}")
    
    # If successful, parse the JSON
    if response.status_code == 200:
        data = response.json()
        
        # Print the response in a structured way
        print("\n=== AI Generation Results ===")
        print(f"AI generated score: {data.get('ai_generated_score')}")
        print(f"Is AI generated: {data.get('is_ai_generated')}")
        
        if data.get('diffusion_score') or data.get('gan_score'):
            print(f"Diffusion score: {data.get('diffusion_score', 0)}")
            print(f"GAN score: {data.get('gan_score', 0)}")
        
        print("\n=== Face Analysis Results ===")
        print(f"Face manipulation score: {data.get('face_manipulation_score')}")
        print(f"Is face manipulated: {data.get('is_face_manipulated')}")
        
        if data.get('face_details'):
            print(f"Number of faces detected: {data['face_details'].get('count', 0)}")
            
            # Print face attributes
            if data['face_details'].get('attributes'):
                for i, face in enumerate(data['face_details']['attributes']):
                    print(f"\nFace #{i+1}:")
                    if face.get('attributes'):
                        if face['attributes'].get('gender'):
                            print(f"  Gender: {face['attributes']['gender']}")
                        if face['attributes'].get('age'):
                            print(f"  Age: {face['attributes']['age']}")
                        if face['attributes'].get('emotion'):
                            print(f"  Emotion: {face['attributes']['emotion']}")
        
        # Display specific model scores if available
        if data.get('specific_models'):
            print("\n=== Specific Model Scores ===")
            
            # Group models by type
            ai_models = {k: v for k, v in data['specific_models'].items() 
                        if not k.startswith('nudity-')}
            nudity_models = {k: v for k, v in data['specific_models'].items() 
                              if k.startswith('nudity-')}
            
            # Print AI models
            if ai_models:
                print("AI models:")
                for model, score in sorted(ai_models.items(), key=lambda x: x[1], reverse=True):
                    print(f"  - {model}: {score:.2f}")
            
            # Print nudity detection matches
            if nudity_models:
                print("\nContent analysis:")
                for model, score in sorted(nudity_models.items(), key=lambda x: x[1], reverse=True):
                    print(f"  - {model}: {score:.2f}")
        
        # Print the raw JSON for debugging
        print("\n=== Raw JSON Response ===")
        print(json.dumps(data, indent=2))
        
    else:
        print(f"Error: {response.text}")
                
except Exception as e:
    print(f"Error: {str(e)}") 