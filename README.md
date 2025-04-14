# ISEWR Backend

This is the FastAPI backend for the ISEWR (Image Search Engine With Recognition) project, integrated with Supabase for storage and database functionality.

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- A Supabase account and project
- The `images` bucket and tables set up in Supabase (see frontend/README-SUPABASE.md)

### Environment Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Update the `.env` file with your Supabase credentials (from the Supabase dashboard)

### Running the Backend

1. Start the server:
   ```bash
   python main.py
   ```

   Or with uvicorn directly:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. The API will be available at http://localhost:8000
3. API documentation is available at http://localhost:8000/docs

## API Endpoints

- **GET /** - Root endpoint, returns a welcome message
- **POST /process** - Process an image with specified edits
- **POST /recognize** - Recognize objects in an image (mock implementation)
- **POST /detect-deepfake** - Detect if a video is a deepfake (mock implementation)
- **POST /convert** - Convert an image to a video (mock implementation)

## Supabase Integration

The backend integrates with Supabase for:

1. Storing processed images in the `images` bucket
2. Recording image metadata in the `images` table
3. Recording processed image metadata in the `processed_images` table

For more details on the Supabase setup, see the `frontend/README-SUPABASE.md` file.

## Making Requests

### Processing an Image with URL

```bash
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -H "X-Process-Type: apply-edits" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "brightness": 120,
    "contrast": 110,
    "rotation": 45,
    "text": "Sample Text",
    "text_x": 100,
    "text_y": 100
  }'
```

### Processing an Image with File Upload

```bash
curl -X POST "http://localhost:8000/process" \
  -H "X-Process-Type: crop" \
  -F "file=@/path/to/your/image.jpg"
``` 