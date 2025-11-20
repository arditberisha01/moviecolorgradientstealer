import os
from supabase import create_client, Client
from typing import Optional, List
import asyncio
from functools import wraps
from datetime import datetime, timedelta

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
    
    async def cleanup_old_files(self, max_age_hours: int = 1):
        """
        Delete old files from Supabase to stay within 1GB free limit.
        Deletes files older than max_age_hours.
        """
        if not self.supabase:
            return
            
        try:
            # List all files in uploads and generated folders
            folders = ["uploads", "generated"]
            
            for folder in folders:
                try:
                    files = self.supabase.storage.from_(self.bucket_name).list(folder)
                    
                    # Delete each file (oldest-first strategy for free plan)
                    for file in files:
                        file_path = f"{folder}/{file['name']}"
                        try:
                            self.supabase.storage.from_(self.bucket_name).remove([file_path])
                            print(f"🗑️  Deleted old file: {file_path}")
                        except Exception as e:
                            print(f"Error deleting {file_path}: {e}")
                            
                except Exception as e:
                    print(f"Error listing files in {folder}: {e}")
                    
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    async def upload_file(self, local_path: str, remote_path: str, cleanup_after: bool = True) -> Optional[str]:
        """
        Upload a file to Supabase Storage.
        If cleanup_after=True, deletes old files to free space (for 1GB free plan).
        """
        if not self.supabase:
            return None
            
        try:
            # Cleanup old files BEFORE uploading to ensure space
            if cleanup_after:
                await self.cleanup_old_files()
            
            with open(local_path, 'rb') as f:
                file_data = f.read()
                
            # Upload to Supabase
            response = self.supabase.storage.from_(self.bucket_name).upload(
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
    
    async def delete_file(self, remote_path: str) -> bool:
        """Delete a specific file from Supabase Storage."""
        if not self.supabase:
            return False
            
        try:
            self.supabase.storage.from_(self.bucket_name).remove([remote_path])
            print(f"🗑️  Deleted: {remote_path}")
            return True
        except Exception as e:
            print(f"Error deleting {remote_path}: {e}")
            return False
    
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

# Singleton instance
storage_manager = StorageManager()
