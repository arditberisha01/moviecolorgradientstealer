import numpy as np
import cv2
from PIL import Image
import ffmpeg
import os
import io
import random
import logging

from app.core.cobalt_client import download_video, search_youtube, cleanup_download

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_frame_useful(frame_np):
    """
    Determines if a frame is good for color analysis.
    Rejects dark frames, solid colors, or extremely low contrast images.
    """
    if frame_np is None or frame_np.size == 0:
        return False
        
    # Convert to grayscale for analysis
    gray = cv2.cvtColor(frame_np, cv2.COLOR_RGB2GRAY)
    
    # 1. Check Brightness
    mean_brightness = np.mean(gray)
    if mean_brightness < 25:  # Too dark (fade to black)
        return False
    if mean_brightness > 245:  # Too bright (fade to white)
        return False
        
    # 2. Check Contrast / Variance
    variance = np.var(gray)
    if variance < 50:  # Solid color or near-solid
        return False
        
    return True


async def search_movies(query: str) -> list[dict]:
    """
    Searches YouTube for movie trailers matching the query.
    Uses lightweight HTML scraping + oEmbed (no yt-dlp needed).
    """
    search_query = f"{query} official trailer 4k"
    try:
        results = await search_youtube(search_query, max_results=5)
        if results:
            logger.info(f"✅ Found {len(results)} results for '{query}'")
            return results
    except Exception as e:
        logger.warning(f"YouTube search failed: {e}")
    
    raise RuntimeError("Video search is currently unavailable. Please try providing a direct URL instead.")


def extract_frame_from_video(video_path: str, timestamp: float = None) -> np.ndarray:
    """Extract a single frame from a local video file."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open video file")

    if timestamp is None:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        target_frame = frame_count // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    else:
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError("Could not read frame from video")

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return frame_rgb


def extract_frame_at_timestamp(video_path: str, timestamp: float) -> np.ndarray:
    """Extract a frame at a specific timestamp using ffmpeg (more reliable for remote-downloaded files)."""
    try:
        out, _ = (
            ffmpeg
            .input(video_path, ss=timestamp)
            .output('pipe:', vframes=1, format='image2', vcodec='png')
            .run(capture_stdout=True, capture_stderr=True)
        )
        image = Image.open(io.BytesIO(out))
        return np.array(image)
    except ffmpeg.Error as e:
        raise RuntimeError(f"ffmpeg error: {e.stderr.decode('utf8')}")
    except Exception as e:
        raise RuntimeError(f"Frame extraction failed: {str(e)}")


async def extract_frame_from_url(url: str, timestamp: float = 0) -> np.ndarray:
    """
    Download a video from URL via Cobalt, extract a frame, clean up.
    Supports YouTube, Instagram, TikTok, Twitter, Reddit, Vimeo, etc.
    """
    video_path = await download_video(url, quality="720")
    
    try:
        frame = extract_frame_at_timestamp(video_path, timestamp)
        return frame
    finally:
        cleanup_download(video_path)


async def extract_multiple_frames_from_url(url: str, target_samples: int = 5) -> list[np.ndarray]:
    """
    Download video via Cobalt, extract multiple frames, filter bad ones.
    Returns the best target_samples frames for color analysis.
    """
    video_path = await download_video(url, quality="720")
    
    try:
        # Get video duration
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Could not open downloaded video")
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 60
        cap.release()
        
        if duration < 5:
            duration = 5
        
        valid_frames = []
        max_attempts = target_samples * 4
        
        # Generate random timestamps in the middle 80% of the video
        timestamps = sorted([
            random.uniform(duration * 0.1, duration * 0.9) 
            for _ in range(max_attempts)
        ])
        
        for ts in timestamps:
            try:
                frame = extract_frame_at_timestamp(video_path, ts)
                if is_frame_useful(frame):
                    valid_frames.append(frame)
                    logger.info(f"✅ Accepted frame at {ts:.1f}s")
                else:
                    logger.info(f"❌ Rejected frame at {ts:.1f}s (dark/blurry)")
                    
                if len(valid_frames) >= target_samples:
                    break
            except Exception as e:
                logger.warning(f"Failed to extract frame at {ts:.1f}s: {e}")
        
        if not valid_frames:
            # Last resort: take a frame from the middle
            logger.warning("Strict filtering rejected all frames. Taking middle frame.")
            try:
                frame = extract_frame_at_timestamp(video_path, duration / 2)
                return [frame]
            except Exception as e:
                raise ValueError(f"Could not extract any frames: {str(e)}")
            
        return valid_frames[:target_samples]
    
    finally:
        cleanup_download(video_path)


# --- Color Science Functions (unchanged) ---

def get_lab_stats(image_np):
    if image_np.shape[2] == 4:
        image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)
    img_lab = cv2.cvtColor(image_np.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    mean = np.mean(img_lab, axis=(0, 1))
    std = np.std(img_lab, axis=(0, 1))
    return mean, std


def get_aggregated_lab_stats(frames: list[np.ndarray]):
    means, stds = [], []
    for frame in frames:
        m, s = get_lab_stats(frame)
        means.append(m)
        stds.append(s)
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


# --- Processing Pipelines ---

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


async def process_url_to_lut(url, timestamp, output_lut_path, output_frame_path=None):
    """Download video via Cobalt, extract frame, generate LUT."""
    frame = await extract_frame_from_url(url, timestamp)
    if output_frame_path:
        Image.fromarray(frame).save(output_frame_path)
    process_image_to_lut(frame, output_lut_path)


async def process_movie_selection_to_lut(video_url, output_lut_path, output_frame_path):
    """
    Download video via Cobalt, sample multiple frames, generate averaged LUT.
    """
    frames = await extract_multiple_frames_from_url(video_url, target_samples=5)
    avg_mean, avg_std = get_aggregated_lab_stats(frames)
    identity = generate_identity_lut(33)
    transformed_lut = apply_color_transfer(identity, avg_mean, avg_std)
    write_cube_file(transformed_lut, output_lut_path, 33)
    # Save first frame as preview
    Image.fromarray(frames[0]).save(output_frame_path)
