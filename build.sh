#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Create necessary directories
mkdir -p /opt/render/project/src/uploads
mkdir -p /opt/render/project/src/uploads/videos

# If we have credentials in environment as base64, write them to a file
# This is already handled in main.py but we'll keep it here for reference
# if [[ -n $GOOGLE_APPLICATION_CREDENTIALS_BASE64 ]]; then
#   echo "Decoding Google Cloud credentials"
#   echo $GOOGLE_APPLICATION_CREDENTIALS_BASE64 | base64 --decode > /opt/render/project/src/google-credentials.json
#   export GOOGLE_APPLICATION_CREDENTIALS=/opt/render/project/src/google-credentials.json
# fi 