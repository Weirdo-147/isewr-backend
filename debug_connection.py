from supabase_client import supabase, store_processed_image
import asyncio
import json

async def test_supabase_connection():
    print("Testing Supabase connection...")
    
    # Check if the client is initialized
    if not supabase:
        print("ERROR: Supabase client is not initialized")
        return
    
    # Test querying the processed_images table
    try:
        print("Querying processed_images table...")
        response = supabase.table("processed_images").select("*").limit(5).execute()
        
        if hasattr(response, 'data') and response.data:
            print(f"Found {len(response.data)} records in processed_images table")
            print(f"Table columns: {list(response.data[0].keys())}")
            print(f"Sample record: {json.dumps(response.data[0], indent=2)}")
        else:
            print("No records found in processed_images table")
    except Exception as e:
        print(f"Error querying table: {str(e)}")
    
    # Test inserting a record
    try:
        print("\nTesting record insertion...")
        test_data = {
            "original_url": "http://test-debug-script.jpg",
            "processed_url": "http://test-debug-processed.jpg"
        }
        
        print(f"Inserting test data: {test_data}")
        result = await store_processed_image(test_data)
        print(f"Insert result: {result}")
    except Exception as e:
        print(f"Error inserting record: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_supabase_connection()) 