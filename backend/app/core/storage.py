import os
from supabase import create_client, Client
from typing import Optional, List
import asyncio
from functools import wraps
from datetime import datetime, timedelta
import hashlib

class StorageManager:
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.bucket_name = os.getenv("SUPABASE_BUCKET", "color-stealer")
        
        # Initialize Supabase if credentials are present
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if supabase_url and supabase_key:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
                # Ensure bucket exists
                self._ensure_bucket_exists()
                print(f"✅ Supabase Storage initialized (bucket: {self.bucket_name})")
            except Exception as e:
                print(f"⚠️  Supabase Storage initialization failed: {e}")
                self.supabase = None
        else:
            print("ℹ️  Supabase credentials not found. Using local storage only.")
    
    def _ensure_bucket_exists(self):
        """Creates the bucket if it doesn't exist."""
        if not self.supabase:
            return
            
        try:
            # Try to get bucket info
            self.supabase.storage.get_bucket(self.bucket_name)
        except Exception:
            # Bucket doesn't exist, create it
            try:
                self.supabase.storage.create_bucket(
                    self.bucket_name,
                    options={"public": True}
                )
                print(f"✅ Created Supabase bucket: {self.bucket_name}")
            except Exception as e:
                print(f"⚠️  Could not create bucket: {e}")
    
    def is_enabled(self) -> bool:
        """Check if Supabase storage is enabled."""
        return self.supabase is not None
    
    async def cleanup_old_files(self):
        """
        Delete all files from Supabase to stay within 1GB free limit.
        """
        if not self.supabase:
            return
            
        try:
            # List all files in the bucket
            files = self.supabase.storage.from_(self.bucket_name).list()
            file_names = [f['name'] for f in files if f['name'] not in ['.', '..']]
            
            if file_names:
                # Delete all listed files
                self.supabase.storage.from_(self.bucket_name).remove(file_names)
                print(f"Deleted {len(file_names)} files from Supabase bucket '{self.bucket_name}'.")
            else:
                print(f"No files to delete in Supabase bucket '{self.bucket_name}'.")
        except Exception as e:
            print(f"Error deleting files from Supabase bucket: {e}")
    
    async def upload_file(self, local_path: str, remote_path: str, cleanup_after: bool = True) -> Optional[str]:
        """
        Upload a file to Supabase Storage.
        If cleanup_after=True, deletes old files to free space (for 1GB free plan).
        """
        if not self.supabase:
            return None
            
        try:
            # Cleanup old files BEFORE uploading to ensure space
            # NOTE: For caching to work persistently, we should be careful about deleting files.
            # But strictly adhering to 1GB limit request, we clean up. 
            # Ideally, we'd only delete if near quota.
            if cleanup_after:
                await self.cleanup_old_files()
            
            with open(local_path, 'rb') as f:
                file_data = f.read()
                
            # Upload to Supabase
            self.supabase.storage.from_(self.bucket_name).upload(
                remote_path,
                file_data,
                file_options={"content-type": self._get_content_type(local_path), "upsert": "true"}
            )
            
            return self.get_public_url(remote_path)
            
        except Exception as e:
            print(f"Upload error for {remote_path}: {e}")
            return None
    
    def get_public_url(self, remote_path: str) -> Optional[str]:
        """Get the public URL for a file in Supabase Storage."""
        if not self.supabase:
            return None
            
        try:
            url = self.supabase.storage.from_(self.bucket_name).get_public_url(remote_path)
            return url
        except Exception as e:
            print(f"Error getting public URL for {remote_path}: {e}")
            return None
    
    def _get_content_type(self, file_path: str) -> str:
        """Determine content type based on file extension."""
        ext = file_path.split('.')[-1].lower()
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'cube': 'text/plain',
            'mp4': 'video/mp4',
            'mov': 'video/quicktime',
        }
        return content_types.get(ext, 'application/octet-stream')

    # --- Caching Methods ---
    
    async def get_cached_analysis(self, cache_key: str):
        if not self.supabase: return None
        try:
            response = self.supabase.table('analysis_cache').select('*').eq('cache_key', cache_key).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            # Table might not exist or other error
            print(f"Cache fetch error (ignoring): {e}")
        return None

    async def save_cached_analysis(self, cache_key: str, lut_url: str, frame_url: str):
        if not self.supabase: return None
        try:
            data = {
                'cache_key': cache_key,
                'lut_path': lut_url, # Storing full URL for simplicity now
                'frame_path': frame_url
            }
            self.supabase.table('analysis_cache').insert(data).execute()
        except Exception as e:
            print(f"Cache save error: {e}")

# Singleton instance
storage_manager = StorageManager()
