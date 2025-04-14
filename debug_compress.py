from supabase_client import supabase, store_processed_image, upload_image_to_bucket
import asyncio
import requests
import uuid
import base64

async def debug_compression_flow():
    print("Debugging compression flow...")
    
    # Check if the client is initialized
    if not supabase:
        print("ERROR: Supabase client is not initialized")
        return
    
    # Test image URL
    test_image_url = "https://picsum.photos/800/600"
    
    # 1. Download the test image
    print(f"Downloading test image from {test_image_url}")
    response = requests.get(test_image_url)
    if response.status_code != 200:
        print(f"Failed to download image, status: {response.status_code}")
        return
    
    image_data = response.content
    print(f"Downloaded image size: {len(image_data)} bytes")
    
    # 2. Upload original to Supabase
    print("Uploading original image to Supabase")
    original_filename = f"debug_original_{uuid.uuid4()}.jpg"
    original_url = await upload_image_to_bucket(image_data, original_filename)
    
    if not original_url:
        print("Failed to upload original image to Supabase")
        return
    
    print(f"Original image uploaded successfully: {original_url}")
    
    # 3. Compress the image (simulated)
    print("Simulating compression (using same image)")
    compressed_data = image_data  # In a real scenario, this would be compressed
    
    # 4. Upload compressed image to Supabase
    print("Uploading compressed image to Supabase")
    compressed_filename = f"debug_compressed_{uuid.uuid4()}.jpg"
    compressed_url = await upload_image_to_bucket(compressed_data, compressed_filename)
    
    if not compressed_url:
        print("Failed to upload compressed image to Supabase")
        return
    
    print(f"Compressed image uploaded successfully: {compressed_url}")
    
    # 5. Store metadata in Supabase
    print("Storing metadata in Supabase")
    processed_data = {
        "original_url": original_url,
        "processed_url": compressed_url
    }
    
    # Add verbose logging to see exactly what's happening in store_processed_image
    print("\n=== DETAILED DEBUGGING OF STORE_PROCESSED_IMAGE ===")
    print(f"Calling store_processed_image with data: {processed_data}")
    result = await store_processed_image(processed_data)
    print(f"Store result: {result}")
    print("=== END OF STORE_PROCESSED_IMAGE DEBUGGING ===\n")
    
    # 6. Verify the record was created
    print("Verifying record was created")
    try:
        # Simple approach: query by the URLs we just used
        response = supabase.table("processed_images").select("*").eq("original_url", original_url).execute()
        
        if hasattr(response, 'data') and response.data:
            print(f"SUCCESS: Found record in processed_images table: {response.data[0]}")
        else:
            print("ERROR: Record not found in processed_images table")
            
            # Try to find the most recent records
            newest_records = supabase.table("processed_images").select("*").order("processed_at", ascending=False).limit(5).execute()
            if hasattr(newest_records, 'data') and newest_records.data:
                print(f"Most recent records: {newest_records.data}")
            else:
                print("No recent records found")
    except Exception as e:
        print(f"Error verifying record: {str(e)}")

if __name__ == "__main__":
    asyncio.run(debug_compression_flow()) 