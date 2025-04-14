import uvicorn
from main import app

# For Vercel and Render serverless deployment
# The handler function is referenced in vercel.json and used by gunicorn
handler = app

# This is for local development
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Starting server on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True) 