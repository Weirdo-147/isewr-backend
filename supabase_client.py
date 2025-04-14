import os
from supabase import create_client, Client
from dotenv import load_dotenv
import time
import requests
import datetime

# Load environment variables
load_dotenv()

# Get Supabase credentials from environment variables
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

def get_supabase_client():
    """Returns the initialized Supabase client"""
    if not supabase:
        print("Warning: Supabase client is not initialized")
    return supabase

def initialize_tables():
    """Ensure required tables exist in Supabase"""
    if not supabase:
        print("Cannot initialize tables - Supabase client is not initialized")
        return
    
    # Note: Table creation requires RLS policy setup as well.
    # Normally you would do this via migration scripts or Supabase UI
    # This is a simplified check to see if the table exists
    try:
        print("Checking if processed_images table exists...")
        
        # Try to query the table
        response = supabase.table("processed_images").select("count", count="exact").limit(1).execute()
        print(f"Table exists, count: {response.count if hasattr(response, 'count') else 'unknown'}")
        
        # Check if video_conversions table exists
        print("Checking if video_conversions table exists...")
        try:
            video_response = supabase.table("video_conversions").select("count", count="exact").limit(1).execute()
            print(f"video_conversions table exists, count: {video_response.count if hasattr(video_response, 'count') else 'unknown'}")
        except Exception as e:
            print(f"Error checking video_conversions table: {str(e)}")
            print("The video_conversions table may not exist. Please create the following table in your Supabase project:")
            print("""
CREATE TABLE video_conversions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_image_url TEXT NOT NULL,
    video_url TEXT,
    prompt TEXT NOT NULL,
    style TEXT NOT NULL,
    aspect_ratio TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Don't forget to set up appropriate RLS policies
            """)
    except Exception as e:
        print(f"Error checking processed_images table: {str(e)}")
        print("The table may not exist. Please create the following table in your Supabase project:")
        print("""
CREATE TABLE processed_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_url TEXT NOT NULL,
    compressed_url TEXT NOT NULL,
    original_size INTEGER NOT NULL,
    compressed_size INTEGER NOT NULL,
    percent_saved NUMERIC(5,2) NOT NULL,
    quality INTEGER NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Don't forget to set up appropriate RLS policies
        """)

# Try to initialize tables when module is imported
try:
    initialize_tables()
except Exception as e:
    print(f"Error during table initialization: {e}")

async def get_image(image_id: str):
    """Get image metadata from Supabase"""
    if not supabase:
        return None
    
    try:
        response = supabase.table("images").select("*").eq("id", image_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error fetching image from Supabase: {e}")
        return None

async def store_processed_image(processed_data: dict):
    """Store processed image metadata in Supabase"""
    if not supabase:
        print("ERROR: Cannot store data - Supabase client is not initialized")
        return None
    
    try:
        print(f"Original data for insert: {processed_data}")
        
        # First, let's check the table structure to adapt to its columns
        try:
            print("Checking table structure...")
            table_query = supabase.table("processed_images").select("*").limit(1).execute()
            
            if hasattr(table_query, 'data') and table_query.data:
                available_columns = list(table_query.data[0].keys())
                print(f"Available columns in processed_images table: {available_columns}")
                
                # Create a new data dictionary with only the columns that exist in the table
                sanitized_data = {}
                
                # Debug print
                print(f"Table has these columns: {available_columns}")
                print(f"Data being added has these fields: {processed_data.keys()}")
                
                # Check if numeric columns exist in the table
                has_original_size = "original_size" in available_columns
                has_compressed_size = "compressed_size" in available_columns
                has_percent_saved = "percent_saved" in available_columns
                has_quality = "quality" in available_columns
                
                print(f"Table has numeric columns: original_size={has_original_size}, compressed_size={has_compressed_size}, percent_saved={has_percent_saved}, quality={has_quality}")
                
                # For numeric values, let's specifically handle them
                if "original_size" in available_columns and processed_data.get("original_size") is not None:
                    try:
                        sanitized_data["original_size"] = int(processed_data["original_size"])
                    except (ValueError, TypeError):
                        sanitized_data["original_size"] = 0
                        print(f"WARNING: Could not convert original_size to int: {processed_data['original_size']}")
                
                if "compressed_size" in available_columns and processed_data.get("compressed_size") is not None:
                    try:
                        sanitized_data["compressed_size"] = int(processed_data["compressed_size"])
                    except (ValueError, TypeError):
                        sanitized_data["compressed_size"] = 0
                        print(f"WARNING: Could not convert compressed_size to int: {processed_data['compressed_size']}")
                
                if "percent_saved" in available_columns and processed_data.get("percent_saved") is not None:
                    try:
                        sanitized_data["percent_saved"] = float(processed_data["percent_saved"])
                    except (ValueError, TypeError):
                        sanitized_data["percent_saved"] = 0.0
                        print(f"WARNING: Could not convert percent_saved to float: {processed_data['percent_saved']}")
                
                if "quality" in available_columns and processed_data.get("quality") is not None:
                    try:
                        sanitized_data["quality"] = int(processed_data["quality"])
                    except (ValueError, TypeError):
                        sanitized_data["quality"] = 85
                        print(f"WARNING: Could not convert quality to int: {processed_data['quality']}")
                
                # Common columns that might exist - we'll include only those that exist
                possible_columns = [
                    "original_url", "compressed_url", "url", "original_size", "compressed_size", 
                    "size", "percent_saved", "quality", "processed_at", "created_at", 
                    "updated_at", "image_id", "description", "file_name", "file_type"
                ]
                
                for col in possible_columns:
                    # If column exists in table and we have data for it
                    if col in available_columns and col in processed_data:
                        sanitized_data[col] = processed_data[col]
                
                # Always ensure we have at least original_url and compressed_url
                # (might be named differently in the table)
                if "original_url" in available_columns and processed_data.get("original_url"):
                    sanitized_data["original_url"] = str(processed_data["original_url"])
                elif "src_url" in available_columns and processed_data.get("original_url"):
                    sanitized_data["src_url"] = str(processed_data["original_url"])
                elif "url" in available_columns and processed_data.get("original_url"):
                    sanitized_data["url"] = str(processed_data["original_url"])
                
                # Use processed_url as the primary column for compressed image URLs
                if "processed_url" in available_columns:
                    if processed_data.get("processed_url"):
                        sanitized_data["processed_url"] = str(processed_data["processed_url"])
                    elif processed_data.get("compressed_url"):
                        # Fallback to compressed_url data if that's what was provided
                        sanitized_data["processed_url"] = str(processed_data["compressed_url"])
                elif "dest_url" in available_columns and processed_data.get("compressed_url"):
                    sanitized_data["dest_url"] = str(processed_data["compressed_url"])
                
                # Add created_at timestamp if it exists
                if "created_at" in available_columns and "created_at" not in sanitized_data:
                    sanitized_data["created_at"] = "now()"
            else:
                print("WARNING: Couldn't fetch table structure. Using default column mapping.")
                sanitized_data = {
                    "original_url": str(processed_data.get("original_url", "")),
                    "processed_url": str(processed_data.get("processed_url", "") or processed_data.get("compressed_url", "")),
                    "processed_at": "now()"
                }
        except Exception as e:
            print(f"WARNING: Error checking table structure: {str(e)}")
            # Use minimal required data for fallback
            sanitized_data = {
                "original_url": str(processed_data.get("original_url", "")),
                "processed_url": str(processed_data.get("processed_url", "") or processed_data.get("compressed_url", "")),
                "processed_at": "now()"
            }
        
        print(f"Sanitized data for insert: {sanitized_data}")
        
        # Insert the data directly
        print("Executing insert...")
        response = supabase.table("processed_images").insert(sanitized_data).execute()
        
        print(f"Insert response: {response}")
        print(f"Insert data: {response.data if hasattr(response, 'data') else 'No data'}")
        
        if hasattr(response, 'data') and response.data:
            return response.data[0]
        else:
            print("WARNING: Insert succeeded but no data returned")
            return {"id": "unknown"}
    except Exception as e:
        print(f"ERROR: Failed to store processed image in Supabase: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Data that failed: {processed_data}")
        return None

async def store_video_conversion(conversion_data: dict):
    """Store video conversion data in Supabase"""
    if not supabase:
        print("ERROR: Cannot store video data - Supabase client is not initialized")
        return None
    
    try:
        # Insert the data directly
        response = supabase.table("video_conversions").insert(conversion_data).execute()
        
        if hasattr(response, 'data') and response.data:
            return response.data[0]
        else:
            print("WARNING: Insert succeeded but no data returned")
            return {"id": "unknown"}
    except Exception as e:
        print(f"ERROR: Failed to store video conversion in Supabase: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Data that failed: {conversion_data}")
        return None

async def update_video_conversion(conversion_id: str, update_data: dict):
    """Update video conversion data in Supabase"""
    if not supabase:
        print("ERROR: Cannot update video data - Supabase client is not initialized")
        return None
    
    try:
        # First, check what columns are available in the table
        try:
            table_info = supabase.table("video_conversions").select("*").limit(1).execute()
            available_columns = []
            if hasattr(table_info, 'data') and len(table_info.data) > 0:
                available_columns = list(table_info.data[0].keys())
                print(f"Available columns in video_conversions: {available_columns}")
            
            # Filter out any keys that don't exist in the table
            filtered_data = {}
            for key, value in update_data.items():
                if key in available_columns:
                    filtered_data[key] = value
                else:
                    print(f"WARNING: Column '{key}' does not exist in video_conversions table and will be skipped")
            
            # Also update the updated_at timestamp if it exists
            if "updated_at" in available_columns:
                filtered_data["updated_at"] = "now()"
            
            # If we have no valid columns to update, return early
            if not filtered_data:
                print("WARNING: No valid columns to update in video_conversions table")
                return {"id": conversion_id, "warning": "No valid columns to update"}
            
            update_data = filtered_data
        except Exception as e:
            print(f"WARNING: Could not check table structure, continuing with update: {e}")
            # Keep using the original update_data
        
        # Update the data directly
        response = supabase.table("video_conversions").update(update_data).eq("id", conversion_id).execute()
        
        if hasattr(response, 'data') and response.data:
            return response.data[0]
        else:
            print("WARNING: Update succeeded but no data returned")
            return {"id": conversion_id}
    except Exception as e:
        print(f"ERROR: Failed to update video conversion in Supabase: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Data that failed: {update_data}")
        return None

async def get_video_conversion(conversion_id: str):
    """Get video conversion data from Supabase"""
    if not supabase:
        return None
    
    try:
        response = supabase.table("video_conversions").select("*").eq("id", conversion_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error fetching video conversion from Supabase: {e}")
        return None

async def upload_image_to_bucket(file_content: bytes, file_name: str):
    """Upload image to Supabase storage bucket"""
    if not supabase:
        return None
    
    try:
        response = supabase.storage.from_("images").upload(file_name, file_content)
        
        # Get public URL
        public_url = supabase.storage.from_("images").get_public_url(file_name)
        return public_url
    except Exception as e:
        print(f"Error uploading to Supabase storage: {e}")
        return None

async def upload_video_to_bucket(file_content: bytes, file_name: str):
    """Upload video to Supabase storage bucket"""
    if not supabase:
        return None
    
    try:
        # Try to use videos bucket if it exists
        try:
            print(f"Uploading video {file_name} to 'videos' bucket...")
            # Ensure the content type is set properly
            content_type = "video/mp4"
            file_options = {"contentType": content_type}
            
            response = supabase.storage.from_("videos").upload(
                file_name, 
                file_content,
                file_options=file_options
            )
            print(f"Upload response: {response}")
            
            # Get public URL
            public_url = supabase.storage.from_("videos").get_public_url(file_name)
            print(f"Public URL: {public_url}")
            
            # Verify the URL works
            try:
                verification = requests.head(public_url, timeout=5)
                print(f"URL verification status: {verification.status_code}")
                if verification.status_code != 200:
                    raise Exception(f"URL verification failed: {verification.status_code}")
            except Exception as e:
                print(f"Warning: URL verification failed: {e}")
                
            return public_url
            
        except Exception as bucket_error:
            print(f"Error using videos bucket, falling back to images bucket: {bucket_error}")
            
            # Fall back to images bucket
            print(f"Uploading video {file_name} to 'images' bucket...")
            content_type = "video/mp4"
            file_options = {"contentType": content_type}
            
            response = supabase.storage.from_("images").upload(
                file_name, 
                file_content,
                file_options=file_options
            )
            print(f"Upload response: {response}")
            
            # Get public URL
            public_url = supabase.storage.from_("images").get_public_url(file_name)
            print(f"Public URL: {public_url}")
            
            # Try to get a signed URL as well (temporary URL with direct access)
            try:
                signed_url = supabase.storage.from_("images").create_signed_url(file_name, 60*60*24) # 24 hour expiry
                print(f"Generated signed URL: {signed_url}")
                # Use signed URL if public URL doesn't work
                verification = requests.head(public_url, timeout=5)
                if verification.status_code != 200 and signed_url:
                    print(f"Using signed URL instead of public URL")
                    return signed_url.get('signedURL')
            except Exception as sign_error:
                print(f"Error getting signed URL: {sign_error}")
            
            return public_url
        
    except Exception as e:
        print(f"Error uploading video to Supabase storage: {e}")
        return None

# Function to store recognition results
async def store_recognition_result(recognition_data):
    """
    Store image recognition results in the recognition_results table.
    
    Args:
        recognition_data (dict): Recognition data with keys: image_url, objects, texts, 
                                scene_description, and web_matches.
    
    Returns:
        dict: The stored record data
    """
    try:
        client = get_supabase_client()
        
        # Ensure all data is in the correct format for PostgreSQL JSON columns
        data_to_store = {
            "image_url": recognition_data.get("image_url", ""),
            "objects": recognition_data.get("objects", []),
            "texts": recognition_data.get("texts", []),
            "scene_description": recognition_data.get("scene_description", ""),
            "web_matches": recognition_data.get("web_matches", []),
            "created_at": datetime.datetime.now().isoformat()
        }
        
        # Insert the data
        response = client.table("recognition_results").insert(data_to_store).execute()
        
        if response.data:
            print(f"Recognition result stored successfully: {response.data[0]['id']}")
            return response.data[0]
        else:
            print("No data returned from recognition result insert")
            return None
    
    except Exception as e:
        print(f"Error storing recognition result: {e}")
        return None

# Function to get recognition results by ID
async def get_recognition_result(recognition_id):
    """
    Get image recognition results by ID.
    
    Args:
        recognition_id (str): The ID of the recognition result to retrieve.
    
    Returns:
        dict: The recognition result data
    """
    try:
        client = get_supabase_client()
        
        # Query the data
        response = client.table("recognition_results").select("*").eq("id", recognition_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            print(f"No recognition result found with ID: {recognition_id}")
            return None
    
    except Exception as e:
        print(f"Error getting recognition result: {e}")
        return None

# Function to update recognition results with celebrity information
async def update_recognition_with_celebrities(recognition_id, celebrities, scene_description):
    """
    Update an existing recognition result with celebrity information.
    
    Args:
        recognition_id (str): The ID of the recognition result to update.
        celebrities (list): List of celebrity names detected.
        scene_description (str): Scene description from celebrity detection.
    
    Returns:
        dict: The updated record data
    """
    try:
        client = get_supabase_client()
        
        # Data to update
        update_data = {
            "celebrities": celebrities,
            "celebrity_scene_description": scene_description,
            "updated_at": datetime.datetime.now().isoformat()
        }
        
        # Update the record
        response = client.table("recognition_results").update(update_data).eq("id", recognition_id).execute()
        
        if response.data and len(response.data) > 0:
            print(f"Recognition result updated with celebrity info: {recognition_id}")
            return response.data[0]
        else:
            print(f"No record updated for recognition ID: {recognition_id}")
            return None
    
    except Exception as e:
        print(f"Error updating recognition result with celebrities: {e}")
        return None 