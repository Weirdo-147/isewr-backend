"""
Test environment setup for Google Cloud services
"""
import os
import sys
import pkg_resources
import importlib.util
from dotenv import load_dotenv
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Load environment variables
load_dotenv()

def check_env_vars() -> Dict[str, bool]:
    """Check that required environment variables are set."""
    results = {}
    
    # Check Google Cloud credentials
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    results['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path is not None
    
    if creds_path is not None:
        # Check if the credentials file exists
        file_exists = Path(creds_path).is_file()
        results['GOOGLE_CREDENTIALS_FILE_EXISTS'] = file_exists
        if not file_exists:
            print(f"Warning: Credentials file specified by GOOGLE_APPLICATION_CREDENTIALS does not exist: {creds_path}")
    
    # Check Google API key
    api_key = os.environ.get('GOOGLE_API_KEY')
    results['GOOGLE_API_KEY'] = api_key is not None
    
    return results

def check_dependencies() -> Dict[str, bool]:
    """Check that required dependencies are installed with correct versions."""
    dependencies = {
        'google-cloud-vision': '3.4.0',
        'google-generativeai': '0.3.0',
        'python-dotenv': '0.15.0',
        'fastapi': '0.95.0',
        'uvicorn': '0.20.0',
        'requests': '2.28.0',
        'python-multipart': '0.0.5',
        'pillow': '9.0.0'
    }
    
    results = {}
    for package, min_version in dependencies.items():
        try:
            installed_version = pkg_resources.get_distribution(package).version
            # Check if installed version meets the minimum version requirement
            meets_requirement = pkg_resources.parse_version(installed_version) >= pkg_resources.parse_version(min_version)
            results[f"{package} (>={min_version})"] = meets_requirement
            if not meets_requirement:
                print(f"Warning: {package} version {installed_version} is installed, but >= {min_version} is required.")
        except pkg_resources.DistributionNotFound:
            results[f"{package} (>={min_version})"] = False
            print(f"Warning: {package} is not installed.")
    
    return results

def check_imports() -> Dict[str, bool]:
    """Check that required modules can be imported."""
    modules = [
        'google.cloud.vision',
        'google.generativeai',
        'dotenv',
        'fastapi',
        'uvicorn',
        'requests',
        'multipart',
        'PIL'
    ]
    
    results = {}
    for module in modules:
        try:
            importlib.import_module(module)
            results[module] = True
        except ImportError as e:
            results[module] = False
            print(f"Warning: Failed to import {module}: {e}")
    
    return results

def check_google_cloud_connectivity() -> Dict[str, bool]:
    """Test connectivity to Google Cloud services."""
    results = {}
    
    # Check if we can access Google Cloud Vision API
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()
        # Just initialize the client, no actual API call needed
        results['google_cloud_vision_connection'] = True
    except Exception as e:
        results['google_cloud_vision_connection'] = False
        print(f"Warning: Could not connect to Google Cloud Vision API: {e}")
    
    # Check if we can access Google Generative AI
    try:
        import google.generativeai as genai
        api_key = os.environ.get('GOOGLE_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            models = genai.list_models()
            # Just check if we can list models
            if models:
                results['google_generativeai_connection'] = True
            else:
                results['google_generativeai_connection'] = False
                print("Warning: Could not list Google Generative AI models. API key may be invalid.")
        else:
            results['google_generativeai_connection'] = False
            print("Warning: Cannot test Google Generative AI connectivity without GOOGLE_API_KEY.")
    except Exception as e:
        results['google_generativeai_connection'] = False
        print(f"Warning: Could not connect to Google Generative AI: {e}")
    
    return results

if __name__ == "__main__":
    print("=== Google Cloud Services Setup Test ===")
    print(f"Python version: {sys.version}")
    
    env_results = check_env_vars()
    dep_results = check_dependencies()
    import_results = check_imports()
    
    print("\n=== Google Cloud Connectivity ===")
    connectivity_results = check_google_cloud_connectivity()
    
    # Combine all results
    all_results = {**env_results, **dep_results, **import_results, **connectivity_results}
    success_count = sum(1 for result in all_results.values() if result)
    total_count = len(all_results)
    
    print("\n=== Summary ===")
    print(f"Passed {success_count}/{total_count} checks")
    
    if success_count < total_count:
        print("\nRecommendations:")
        if not env_results.get('GOOGLE_APPLICATION_CREDENTIALS', False):
            print("- Set the GOOGLE_APPLICATION_CREDENTIALS environment variable to the path of your Google Cloud credentials JSON file")
        if not env_results.get('GOOGLE_CREDENTIALS_FILE_EXISTS', False) and env_results.get('GOOGLE_APPLICATION_CREDENTIALS', False):
            print("- Ensure that the Google Cloud credentials file exists at the specified path")
        if not env_results.get('GOOGLE_API_KEY', False):
            print("- Set the GOOGLE_API_KEY environment variable")
        
        missing_deps = [dep.split(' ')[0] for dep, result in dep_results.items() if not result]
        if missing_deps:
            print(f"- Install missing dependencies: pip install {' '.join(missing_deps)}")
        
        if not connectivity_results.get('google_cloud_vision_connection', False) or not connectivity_results.get('google_generativeai_connection', False):
            print("- Verify your Google Cloud project is properly set up and APIs are enabled")
            
        sys.exit(1)
    else:
        print("\nAll checks passed! The environment is correctly set up.")
        sys.exit(0)
        
    if not env_results.get('GOOGLE_APPLICATION_CREDENTIALS', False):
        print("\nEnvironment Variables Help:")
        print("1. Create a .env file in the backend directory")
        print("2. Set the following variables:")
        print("   GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account-key.json")
        print("   GOOGLE_API_KEY=your_api_key_here")
        
    if not dep_results.get('google-cloud-vision', False) or not dep_results.get('google-generativeai', False):
        print("\nDependency Installation Help:")
        print("Run: pip install -r requirements.txt")
        print("Or install missing packages individually with: pip install package-name==version") 