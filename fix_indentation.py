import re

# Open the file and read its content
with open('main.py', 'r') as file:
    content = file.read()

# Fix try block indentation around line 500
fixed_content = re.sub(r'try:\s*\n\s*# Save the uploaded file', 'try:\n        # Save the uploaded file', content)
fixed_content = re.sub(r'\n    if mode == "aggressive":', '\n        if mode == "aggressive":', fixed_content)

# Fix all indented blocks to ensure they're properly aligned
# First, fix "if not findings:" block
fixed_content = re.sub(r'if not findings:\s*\n\s*findings =', 'if not findings:\n                    findings =', fixed_content)
fixed_content = re.sub(r']\s*\n\s*return {', ']\n                \n                return {', fixed_content)

# Fix return statement indentation
fixed_content = re.sub(r'"success": True,\s*\n\s*"message":', '"success": True,\n                    "message":', fixed_content)
fixed_content = re.sub(r'"video_id": video_id,\s*\n\s*"confidence":', '"video_id": video_id,\n                    "confidence":', fixed_content)
fixed_content = re.sub(r'"face_confidence": face_confidence,\s*\n\s*"lip_sync_confidence":', '"face_confidence": face_confidence,\n                    "lip_sync_confidence":', fixed_content)

# Write the fixed content back to the main.py file directly
with open('main.py', 'w') as file:
    file.write(fixed_content)

print("Fixed indentation issues in main.py") 