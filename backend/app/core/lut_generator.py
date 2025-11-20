import numpy as np
import cv2
from PIL import Image
import ffmpeg
import yt_dlp
import os
import io
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_ydl_opts(base_opts=None):
    """
    Returns standard yt-dlp options with bot bypass and cookie support.
    """
    # Strategy: Use iOS client as primary
    opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb'],
                'skip': ['hls', 'dash', 'translated_subs']
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
        }
    }
    
    # Check for cookies file (useful for local dev or if mounted)
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'
    elif os.getenv('YOUTUBE_COOKIES_CONTENT'):
        # If passed as env var, write to temp file
        try:
            with open('cookies_temp.txt', 'w') as f:
                f.write(os.getenv('YOUTUBE_COOKIES_CONTENT'))
            opts['cookiefile'] = 'cookies_temp.txt'
        except Exception as e:
            logger.warning(f"Failed to write cookies from env: {e}")

    if base_opts:
        opts.update(base_opts)
    return opts

def search_movies(query: str) -> list[dict]:
    """
    Searches YouTube for the query and returns a list of results.
    """
    search_query = f"{query} official trailer 4k"
    ydl_opts = get_ydl_opts({
        'format': 'best[ext=mp4]/best',
        'default_search': 'ytsearch5:', # Search for top 5 results
        'extract_flat': True, # Don't download, just get metadata
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            
            results = []
            if 'entries' in info:
                for entry in info['entries']:
                    # Some entries might be None or playlists, skip them
                    if not entry: 
                        continue
                        
                    # Handle flat extraction data structure
                    results.append({
                        'title': entry.get('title', 'Unknown Title'),
                        'url': entry.get('url', ''),
                        'thumbnail': entry.get('thumbnail', None),
                        'duration': entry.get('duration', 0),
                        'view_count': entry.get('view_count', 0)
                    })
            
            if not results:
                # Fallback: if no entries found (sometimes yt-dlp structure varies)
                if 'url' in info:
                     results.append({
                        'title': info.get('title', 'Unknown Title'),
                        'url': info.get('url', ''),
                        'thumbnail': info.get('thumbnail', None),
                         'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0)
                    })
            
            if not results:
                raise ValueError("No video results found")
                
            return results

    except Exception as e:
        # Fallback strategy (Android client) if iOS fails
        logger.warning(f"iOS search failed: {e}. Retrying with Android...")
        ydl_opts['extractor_args']['youtube']['player_client'] = ['android']
        ydl_opts['http_headers']['User-Agent'] = 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip'
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                results = []
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            results.append({
                                'title': entry.get('title', 'Unknown Title'),
                                'url': entry.get('url', ''),
                                'thumbnail': entry.get('thumbnail', None),
                                'duration': entry.get('duration', 0),
                                'view_count': entry.get('view_count', 0)
                            })
                return results
        except Exception as e2:
            raise RuntimeError(f"Search failed: {str(e2)}")

def extract_frame_from_video(video_path: str, timestamp: float = None) -> np.ndarray:
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

def extract_frame_from_url(url: str, timestamp: float = 0) -> np.ndarray:
    # If youtube/vimeo, extract real URL
    if "youtube.com" in url or "youtu.be" in url or "vimeo.com" in url:
        ydl_opts = get_ydl_opts({'format': 'best[ext=mp4]/best'})
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_url = info['url']
        except Exception as e:
            # Retry with Android
            logger.warning(f"iOS extract failed: {e}. Retrying with Android...")
            ydl_opts['extractor_args']['youtube']['player_client'] = ['android']
            ydl_opts['http_headers']['User-Agent'] = 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip'
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    video_url = info['url']
            except Exception as e2:
                raise RuntimeError(f"Failed to extract video URL: {str(e2)}")
    else:
        video_url = url
        
    # ffmpeg extraction
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
    ydl_opts = get_ydl_opts({'format': 'best[ext=mp4]/best'})
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info['url']
            duration = info.get('duration', 60)
    except Exception as e:
        # Retry with Android
        logger.warning(f"iOS multi-extract failed: {e}. Retrying with Android...")
        ydl_opts['extractor_args']['youtube']['player_client'] = ['android']
        ydl_opts['http_headers']['User-Agent'] = 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip'
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_url = info['url']
                duration = info.get('duration', 60)
        except Exception as e2:
             raise RuntimeError(f"Failed to extract video URL: {str(e2)}")

    frames = []
    # Avoid the very beginning and very end
    if duration < 5: duration = 5 # Minimum duration safety
    timestamps = sorted([random.uniform(duration * 0.15, duration * 0.85) for _ in range(num_samples)])
    
    for ts in timestamps:
        try:
            frame = extract_frame_from_url(video_url, ts)
            frames.append(frame)
        except Exception as e:
            logger.warning(f"Failed to extract frame at {ts}: {e}")
            
    if not frames:
        raise ValueError("Could not extract any frames from the video")
        
    return frames

# --- Color Science Functions (Unchanged) ---
def get_lab_stats(image_np):
    if image_np.shape[2] == 4: image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)
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

def process_url_to_lut(url, timestamp, output_lut_path, output_frame_path=None):
    frame = extract_frame_from_url(url, timestamp)
    if output_frame_path:
        Image.fromarray(frame).save(output_frame_path)
    process_image_to_lut(frame, output_lut_path)

def process_movie_selection_to_lut(video_url, output_lut_path, output_frame_path):
    """
    Processes a specific selected movie trailer URL.
    """
    frames = extract_multiple_frames_from_url(video_url, num_samples=5)
    avg_mean, avg_std = get_aggregated_lab_stats(frames)
    identity = generate_identity_lut(33)
    transformed_lut = apply_color_transfer(identity, avg_mean, avg_std)
    write_cube_file(transformed_lut, output_lut_path, 33)
    # Save first frame as preview
    Image.fromarray(frames[0]).save(output_frame_path)
