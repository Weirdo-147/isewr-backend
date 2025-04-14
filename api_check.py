import os
import sys
from dotenv import load_dotenv

def check_env():
    print("Checking environment variables loading:")
    # Load environment variables from .env file
    load_dotenv()
    
    # Print all environment variables
    print("\nEnvironment variables:")
    sightengine_api_user = os.getenv("SIGHTENGINE_API_USER")
    sightengine_api_secret = os.getenv("SIGHTENGINE_API_SECRET")
    
    print(f"SIGHTENGINE_API_USER: {sightengine_api_user}")
    print(f"SIGHTENGINE_API_SECRET: {sightengine_api_secret[:5]}... (length: {len(sightengine_api_secret) if sightengine_api_secret else 0})")
    
    # Check if variables are in environment
    print("\nEnvironment checks:")
    print(f"SIGHTENGINE_API_USER in os.environ: {'SIGHTENGINE_API_USER' in os.environ}")
    print(f"SIGHTENGINE_API_SECRET in os.environ: {'SIGHTENGINE_API_SECRET' in os.environ}")
    
    # Check Python and dotenv version
    print("\nVersions:")
    print(f"Python version: {sys.version}")
    print(f"dotenv path: {load_dotenv.__module__}")
    
    # Print working directory
    print(f"\nCurrent working directory: {os.getcwd()}")
    
    # Check if .env file exists
    env_path = os.path.join(os.getcwd(), ".env")
    print(f".env file exists: {os.path.exists(env_path)}")
    
    # If .env exists, print its size and first few lines
    if os.path.exists(env_path):
        print(f".env file size: {os.path.getsize(env_path)} bytes")
        with open(env_path, 'r') as f:
            lines = f.readlines()
            print(f".env file line count: {len(lines)}")
            
            # Print redacted version of first 5 lines
            print("\nFirst few lines of .env (redacted):")
            for i, line in enumerate(lines[:5]):
                if i < len(lines):
                    # Redact sensitive information
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        if value and len(value) > 5:
                            redacted = value[:3] + '*' * (len(value) - 6) + value[-3:]
                            print(f"{key}={redacted}")
                        else:
                            print(f"{key}={value}")
                    else:
                        print(line.strip())

if __name__ == "__main__":
    check_env() 