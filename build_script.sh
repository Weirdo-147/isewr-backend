#!/bin/bash
pip install -r requirements.txt
python -c "import os; os.makedirs('uploads', exist_ok=True); os.makedirs('uploads/videos', exist_ok=True)" 