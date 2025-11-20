import numpy as np
import cv2
from PIL import Image
import ffmpeg
import yt_dlp
import os
import io
import random

def extract_frame_from_video(video_path: str, timestamp: float = None) -> np.ndarray:
    """
    Extracts a frame from a video file.
    If timestamp is None, extracts the middle frame.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open video file")

    if timestamp is None:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        target_frame = frame_count // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    else:
        # timestamp is in seconds. OpenCV expects milliseconds for POS_MSEC
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError("Could not read frame from video")

    # Convert BGR (OpenCV) to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return frame_rgb

def get_video_url_from_query(query: str) -> str:
    """
    Searches YouTube for the query (e.g. "Dune trailer") and returns the first video URL.
    """
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'default_search': 'ytsearch1:',
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'skip': ['hls', 'dash']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info:
            video_url = info['entries'][0]['url']
        else:
            video_url = info['url']
            
    return video_url

def extract_frame_from_url(url: str, timestamp: float = 0) -> np.ndarray:
    """
    Extracts a frame from a URL using yt-dlp and ffmpeg streaming.
    """
    # 1. Get direct stream URL (if not already a direct link)
    # If it's a youtube link, resolve it. If it's a direct stream, use it.
    if "youtube.com" in url or "youtu.be" in url or "vimeo.com" in url:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'skip': ['hls', 'dash']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            }
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_url = info['url']
        except Exception as e:
            raise RuntimeError(f"Failed to extract video URL: {str(e)}")
    else:
        video_url = url
        
    # 2. Use ffmpeg to seek and capture 1 frame
    try:
        out, _ = (
            ffmpeg
            .input(video_url, ss=timestamp)
            .output('pipe:', vframes=1, format='image2', vcodec='png')
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        image = Image.open(io.BytesIO(out))
        return np.array(image)
        
    except ffmpeg.Error as e:
        raise RuntimeError(f"ffmpeg error: {e.stderr.decode('utf8')}")
    except Exception as e:
        raise RuntimeError(f"Frame extraction failed: {str(e)}")

def extract_multiple_frames_from_url(url: str, num_samples: int = 5) -> list[np.ndarray]:
    """
    Extracts multiple random frames from a YouTube URL to analyze the overall look.
    """
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'skip': ['hls', 'dash']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_url = info['url']
        duration = info.get('duration', 60) # Default to 60s if unknown

    frames = []
    # Pick random timestamps from 10% to 90% of the video
    timestamps = sorted([random.uniform(duration * 0.1, duration * 0.9) for _ in range(num_samples)])
    
    for ts in timestamps:
        try:
            frame = extract_frame_from_url(video_url, ts)
            frames.append(frame)
        except Exception as e:
            print(f"Failed to extract frame at {ts}: {e}")
            
    if not frames:
        raise ValueError("Could not extract any frames from the video")
        
    return frames

def get_lab_stats(image_np):
    """
    Calculates mean and standard deviation in LAB color space.
    """
    # Ensure RGB
    if image_np.shape[2] == 4: # RGBA
        image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)
        
    img_lab = cv2.cvtColor(image_np.astype(np.uint8), cv2.COLOR_RGB2LAB)
    img_lab = img_lab.astype(np.float32)
    
    mean = np.mean(img_lab, axis=(0, 1))
    std = np.std(img_lab, axis=(0, 1))
    return mean, std

def get_aggregated_lab_stats(frames: list[np.ndarray]):
    """
    Calculates averaged mean and std dev across multiple frames.
    """
    means = []
    stds = []
    
    for frame in frames:
        m, s = get_lab_stats(frame)
        means.append(m)
        stds.append(s)
        
    # Simple averaging of statistics
    avg_mean = np.mean(means, axis=0)
    avg_std = np.mean(stds, axis=0)
    
    return avg_mean, avg_std

def generate_identity_lut(size=33):
    x = np.linspace(0, 255, size)
    y = np.linspace(0, 255, size)
    z = np.linspace(0, 255, size)
    B, G, R = np.meshgrid(z, y, x, indexing='ij')
    lut = np.stack([R, G, B], axis=-1)
    return lut.astype(np.float32)

def apply_color_transfer(identity_lut, target_mean, target_std):
    h, w, d, c = identity_lut.shape
    lut_flat = identity_lut.reshape(-1, 3)
    
    lut_image = lut_flat.reshape(h * w, d, 3).astype(np.uint8)
    lut_lab = cv2.cvtColor(lut_image, cv2.COLOR_RGB2LAB).astype(np.float32)
    l, a, b = cv2.split(lut_lab)
    
    # Identity LUT stats (Source)
    l_mean, l_std = np.mean(l), np.std(l)
    a_mean, a_std = np.mean(a), np.std(a)
    b_mean, b_std = np.mean(b), np.std(b)
    
    src_means = [l_mean, a_mean, b_mean]
    src_stds = [l_std, a_std, b_std]
    channels = [l, a, b]
    res_channels = []
    
    for i in range(3):
        ch = channels[i]
        ch = ch - src_means[i]
        # Scale factor with dampening to prevent extreme contrast
        scale = target_std[i] / (src_stds[i] + 1e-6)
        ch = ch * scale
        ch = ch + target_mean[i]
        res_channels.append(ch)
        
    result_lab = cv2.merge(res_channels)
    result_rgb = cv2.cvtColor(result_lab.astype(np.float32), cv2.COLOR_LAB2RGB)
    result_rgb = np.clip(result_rgb, 0, 255)
    
    return result_rgb.reshape(h, w, d, 3)

def write_cube_file(lut_rgb, file_path, size=33):
    with open(file_path, 'w') as f:
        f.write(f'TITLE "Generated by Color Stealer"\n')
        f.write(f'LUT_3D_SIZE {size}\n')
        for z in range(size):
            for y in range(size):
                for x in range(size):
                    r, g, b = lut_rgb[z, y, x]
                    f.write(f'{r/255.0:.6f} {g/255.0:.6f} {b/255.0:.6f}\n')

def process_image_to_lut(image_np, output_lut_path):
    target_mean, target_std = get_lab_stats(image_np)
    identity = generate_identity_lut(33)
    transformed_lut = apply_color_transfer(identity, target_mean, target_std)
    write_cube_file(transformed_lut, output_lut_path, 33)

def process_video_to_lut(video_path, output_lut_path, output_frame_path=None, timestamp=None):
    frame = extract_frame_from_video(video_path, timestamp)
    if output_frame_path:
        Image.fromarray(frame).save(output_frame_path)
    process_image_to_lut(frame, output_lut_path)

def process_url_to_lut(url, timestamp, output_lut_path, output_frame_path=None):
    frame = extract_frame_from_url(url, timestamp)
    if output_frame_path:
        Image.fromarray(frame).save(output_frame_path)
    process_image_to_lut(frame, output_lut_path)

def process_movie_query_to_lut(query, output_lut_path, output_frame_path):
    """
    Full pipeline for Movie Search -> LUT
    1. Find video URL from query
    2. Extract multiple frames
    3. Aggregate stats
    4. Generate LUT
    5. Save a representative frame (the first one)
    """
    # 1. Search
    full_query = f"{query} official trailer 4k"
    video_url = get_video_url_from_query(full_query)
    
    # 2. Extract Frames
    frames = extract_multiple_frames_from_url(video_url, num_samples=5)
    
    # 3. Aggregate Stats
    avg_mean, avg_std = get_aggregated_lab_stats(frames)
    
    # 4. Generate LUT
    identity = generate_identity_lut(33)
    transformed_lut = apply_color_transfer(identity, avg_mean, avg_std)
    write_cube_file(transformed_lut, output_lut_path, 33)
    
    # 5. Save Preview (use the first frame as reference)
    Image.fromarray(frames[0]).save(output_frame_path)
