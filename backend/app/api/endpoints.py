from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Body
from fastapi.responses import FileResponse
import shutil
import os
import uuid
from typing import Optional
from pydantic import BaseModel
import numpy as np
from PIL import Image
import io
from app.core.lut_generator import process_video_to_lut, process_image_to_lut, process_url_to_lut, process_movie_query_to_lut

router = APIRouter()

DATA_DIR = os.getenv("DATA_DIR", "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
GENERATED_DIR = os.path.join(DATA_DIR, "generated")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

class UrlRequest(BaseModel):
    url: str
    timestamp: float = 0.0

class MovieRequest(BaseModel):
    query: str

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_ext = file.filename.split('.')[-1]
    video_filename = f"{file_id}.{file_ext}"
    video_path = os.path.join(UPLOAD_DIR, video_filename)
    
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "lut_url": f"/api/download/generated/{lut_filename}",
        "frame_url": f"/api/download/generated/{frame_filename}"
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
        
        # Convert to RGB and save for preview
        if image.mode in ('RGBA', 'P'): 
            image = image.convert('RGB')
        image.save(frame_path)
        
        # Convert to numpy for processing
        image_np = np.array(image)
        process_image_to_lut(image_np, lut_path)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "lut_url": f"/api/download/generated/{lut_filename}",
        "frame_url": f"/api/download/generated/{frame_filename}"
    }

@router.post("/generate-from-url")
async def generate_from_url(request: UrlRequest):
    file_id = str(uuid.uuid4())
    lut_filename = f"{file_id}.cube"
    frame_filename = f"{file_id}.jpg"
    lut_path = os.path.join(GENERATED_DIR, lut_filename)
    frame_path = os.path.join(GENERATED_DIR, frame_filename)
    
    try:
        process_url_to_lut(request.url, request.timestamp, lut_path, frame_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "lut_url": f"/api/download/generated/{lut_filename}",
        "frame_url": f"/api/download/generated/{frame_filename}"
    }

@router.post("/analyze-movie")
async def analyze_movie(request: MovieRequest):
    file_id = str(uuid.uuid4())
    lut_filename = f"{file_id}.cube"
    frame_filename = f"{file_id}.jpg"
    lut_path = os.path.join(GENERATED_DIR, lut_filename)
    frame_path = os.path.join(GENERATED_DIR, frame_filename)
    
    try:
        process_movie_query_to_lut(request.query, lut_path, frame_path)
    except Exception as e:
        # Print error for debugging
        print(f"Movie analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze movie: {str(e)}")
        
    return {
        "lut_url": f"/api/download/generated/{lut_filename}",
        "frame_url": f"/api/download/generated/{frame_filename}"
    }

@router.get("/download/generated/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(GENERATED_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
