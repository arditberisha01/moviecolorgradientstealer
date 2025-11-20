import os
from supabase import create_client, Client
from typing import Optional
import asyncio
from functools import wraps

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
    
    async def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """Upload a file to Supabase Storage."""
        if not self.supabase:
            return None
            
        try:
            with open(local_path, 'rb') as f:
                file_data = f.read()
                
            # Upload to Supabase
            response = self.supabase.storage.from_(self.bucket_name).upload(
                remote_path,
                file_data,
                file_options={"content-type": self._get_content_type(local_path)}
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

# Singleton instance
storage_manager = StorageManager()

