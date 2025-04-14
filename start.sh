#!/bin/bash

# Start the FastAPI application
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} 