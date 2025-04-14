import uvicorn
from main import app

# This is for local development
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# For Vercel serverless deployment
# The handler function is referenced in vercel.json
handler = app 