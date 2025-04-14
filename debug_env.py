from dotenv import load_dotenv
import os

load_dotenv()

print("Checking SightEngine API credentials:")
print(f"SIGHTENGINE_API_USER: {os.getenv('SIGHTENGINE_API_USER')}")
print(f"SIGHTENGINE_API_SECRET: {os.getenv('SIGHTENGINE_API_SECRET')}")

# Also check if the variables are in the environment
print("\nChecking if variables are in os.environ:")
print(f"SIGHTENGINE_API_USER in os.environ: {'SIGHTENGINE_API_USER' in os.environ}")
print(f"SIGHTENGINE_API_SECRET in os.environ: {'SIGHTENGINE_API_SECRET' in os.environ}") 