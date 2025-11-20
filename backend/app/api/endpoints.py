from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Body
from fastapi.responses import FileResponse, RedirectResponse
import shutil
import os
import uuid
from typing import Optional, List
from pydantic import BaseModel
import numpy as np
from PIL import Image
import io
import hashlib
from app.core.lut_generator import (
    process_video_to_lut, 
    process_image_to_lut, 
    process_url_to_lut, 
    search_movies,
    process_movie_selection_to_lut
)
from app.core.storage import storage_manager

router = APIRouter()

DATA_DIR = os.getenv("DATA_DIR", "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
GENERATED_DIR = os.path.join(DATA_DIR, "generated")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

class UrlRequest(BaseModel):
    url: str
    timestamp: float = 0.0

class MovieSearchRequest(BaseModel):
    query: str

class MovieSelectionRequest(BaseModel):
    url: str

def generate_cache_key(prefix: str, data: str) -> str:
    return hashlib.md5(f"{prefix}:{data}".encode()).hexdigest()

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_ext = file.filename.split('.')[-1]
    video_filename = f"{file_id}.{file_ext}"
    
    # Save locally first (for processing)
    video_path = os.path.join(UPLOAD_DIR, video_filename)
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Optionally upload to Supabase
    if storage_manager.is_enabled():
        try:
            await storage_manager.upload_file(video_path, f"uploads/{video_filename}", cleanup_after=True)
        except Exception as e:
            print(f"Supabase upload failed (continuing with local): {e}")
        
    return {"file_id": file_id, "filename": video_filename}

@router.post("/generate-lut/{file_id}")
async def generate_lut(file_id: str, timestamp: float = Body(None, embed=True)):
    video_path = None
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(file_id):
            video_path = os.path.join(UPLOAD_DIR, f)
            break
            
    if not video_path:
        raise HTTPException(status_code=404, detail="Video not found")
        
    lut_filename = f"{file_id}.cube"
    frame_filename = f"{file_id}.jpg"
    lut_path = os.path.join(GENERATED_DIR, lut_filename)
    frame_path = os.path.join(GENERATED_DIR, frame_filename)
    
    try:
        process_video_to_lut(video_path, lut_path, frame_path, timestamp)
        
        # Upload results to Supabase
        lut_url = f"/api/download/generated/{lut_filename}"
        frame_url = f"/api/download/generated/{frame_filename}"

        if storage_manager.is_enabled():
            # Don't cleanup here to preserve upload
            l_url = await storage_manager.upload_file(lut_path, f"generated/{lut_filename}", cleanup_after=False)
            f_url = await storage_manager.upload_file(frame_path, f"generated/{frame_filename}", cleanup_after=False)
            if l_url: lut_url = l_url
            if f_url: frame_url = f_url
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "lut_url": lut_url,
        "frame_url": frame_url
    }

@router.post("/generate-from-image")
async def generate_from_image(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    lut_filename = f"{file_id}.cube"
    frame_filename = f"{file_id}.jpg"
    lut_path = os.path.join(GENERATED_DIR, lut_filename)
    frame_path = os.path.join(GENERATED_DIR, frame_filename)
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        if image.mode in ('RGBA', 'P'): 
            image = image.convert('RGB')
        image.save(frame_path)
        
        image_np = np.array(image)
        process_image_to_lut(image_np, lut_path)
        
        # Upload to Supabase
        lut_url = f"/api/download/generated/{lut_filename}"
        frame_url = f"/api/download/generated/{frame_filename}"

        if storage_manager.is_enabled():
            l_url = await storage_manager.upload_file(lut_path, f"generated/{lut_filename}")
            f_url = await storage_manager.upload_file(frame_path, f"generated/{frame_filename}", cleanup_after=False)
            if l_url: lut_url = l_url
            if f_url: frame_url = f_url
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "lut_url": lut_url,
        "frame_url": frame_url
    }

@router.post("/generate-from-url")
async def generate_from_url(request: UrlRequest):
    # Check cache
    cache_key = generate_cache_key("url", f"{request.url}:{request.timestamp}")
    cached = await storage_manager.get_cached_analysis(cache_key)
    if cached:
        return {
            "lut_url": cached['lut_path'],
            "frame_url": cached['frame_path']
        }

    file_id = str(uuid.uuid4())
    lut_filename = f"{file_id}.cube"
    frame_filename = f"{file_id}.jpg"
    lut_path = os.path.join(GENERATED_DIR, lut_filename)
    frame_path = os.path.join(GENERATED_DIR, frame_filename)
    
    try:
        process_url_to_lut(request.url, request.timestamp, lut_path, frame_path)
        
        lut_url = f"/api/download/generated/{lut_filename}"
        frame_url = f"/api/download/generated/{frame_filename}"

        if storage_manager.is_enabled():
            l_url = await storage_manager.upload_file(lut_path, f"generated/{lut_filename}")
            f_url = await storage_manager.upload_file(frame_path, f"generated/{frame_filename}", cleanup_after=False)
            if l_url: lut_url = l_url
            if f_url: frame_url = f_url
            
            # Save to cache
            await storage_manager.save_cached_analysis(cache_key, lut_url, frame_url)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "lut_url": lut_url,
        "frame_url": frame_url
    }

@router.post("/search-movie")
async def search_movie_endpoint(request: MovieSearchRequest):
    try:
        results = search_movies(request.query)
        return {"results": results}
    except Exception as e:
        print(f"Movie search error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search movie: {str(e)}")

@router.post("/analyze-movie-selection")
async def analyze_movie_selection(request: MovieSelectionRequest):
    # Check cache
    cache_key = generate_cache_key("movie", request.url)
    cached = await storage_manager.get_cached_analysis(cache_key)
    if cached:
        return {
            "lut_url": cached['lut_path'],
            "frame_url": cached['frame_path']
        }

    file_id = str(uuid.uuid4())
    lut_filename = f"{file_id}.cube"
    frame_filename = f"{file_id}.jpg"
    lut_path = os.path.join(GENERATED_DIR, lut_filename)
    frame_path = os.path.join(GENERATED_DIR, frame_filename)
    
    try:
        process_movie_selection_to_lut(request.url, lut_path, frame_path)
        
        lut_url = f"/api/download/generated/{lut_filename}"
        frame_url = f"/api/download/generated/{frame_filename}"

        if storage_manager.is_enabled():
            l_url = await storage_manager.upload_file(lut_path, f"generated/{lut_filename}")
            f_url = await storage_manager.upload_file(frame_path, f"generated/{frame_filename}", cleanup_after=False)
            if l_url: lut_url = l_url
            if f_url: frame_url = f_url
            
            # Save to cache
            await storage_manager.save_cached_analysis(cache_key, lut_url, frame_url)
            
    except Exception as e:
        print(f"Movie analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze movie: {str(e)}")
        
    return {
        "lut_url": lut_url,
        "frame_url": frame_url
    }

@router.get("/download/generated/{filename}")
async def download_file(filename: str):
    # Try Supabase first
    if storage_manager.is_enabled():
        public_url = storage_manager.get_public_url(f"generated/{filename}")
        if public_url:
            return RedirectResponse(url=public_url)
    
    # Fallback to local
    file_path = os.path.join(GENERATED_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
