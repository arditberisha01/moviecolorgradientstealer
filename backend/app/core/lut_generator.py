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
    opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'tv', 'web'],
                'player_skip': ['webpage', 'configs'],
                'skip': ['hls', 'dash', 'translated_subs']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        }
    }
    
    # Add proxy support from environment (useful for Render deployment with rotating proxies)
    proxy_ip = os.getenv('proxy-ip') or os.getenv('PROXY_IP')
    proxy_username = os.getenv('username') or os.getenv('PROXY_USERNAME')
    proxy_password = os.getenv('password') or os.getenv('PROXY_PASSWORD')
    proxy_port = os.getenv('http-port') or os.getenv('PROXY_PORT')
    
    if proxy_ip and proxy_port:
        if proxy_username and proxy_password:
            opts['proxy'] = f"http://{proxy_username}:{proxy_password}@{proxy_ip}:{proxy_port}"
        else:
            opts['proxy'] = f"http://{proxy_ip}:{proxy_port}"
    
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'
    elif os.getenv('YOUTUBE_COOKIES_CONTENT'):
        try:
            with open('cookies_temp.txt', 'w') as f:
                f.write(os.getenv('YOUTUBE_COOKIES_CONTENT'))
            opts['cookiefile'] = 'cookies_temp.txt'
        except Exception as e:
            logger.warning(f"Failed to write cookies from env: {e}")

    if base_opts:
        opts.update(base_opts)
    return opts

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
    if mean_brightness < 25: # Too dark (fade to black)
        return False
    if mean_brightness > 245: # Too bright (fade to white)
        return False
        
    # 2. Check Contrast / Variance
    # A solid color screen (like a logo or black screen) has very low variance
    variance = np.var(gray)
    if variance < 200: # Threshold found via experimentation for "flat" images
        return False
        
    return True

def search_movies(query: str) -> list[dict]:
    """
    Searches YouTube for the query and returns a list of results.
    """
    search_query = f"{query} official trailer 4k"
    ydl_opts = get_ydl_opts({
        'format': 'best[ext=mp4]/best',
        'default_search': 'ytsearch5:',
        'extract_flat': True,
    })
    
    # Keep player_client if it exists, it helps with bot bypass
    if 'extractor_args' in ydl_opts and 'youtube' in ydl_opts['extractor_args']:
        logger.info(f"Using player_client: {ydl_opts['extractor_args']['youtube'].get('player_client')}")

    proxy_str = ydl_opts.get('proxy', 'No Proxy')
    logger.info(f"🔎 Starting search for: '{search_query}' using proxy: {proxy_str}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            results = []
            
            # Handle list of results
            if 'entries' in info:
                entries = info['entries']
                logger.info(f"Found {len(entries)} potential entries")
                for entry in entries:
                    if not entry: continue
                    url = entry.get('url') or entry.get('webpage_url') or ""
                    # Enhanced filtering for garbage results
                    if not url or url.startswith('ytsearch') or entry.get('_type') == 'url':
                        continue
                        
                    results.append({
                        'title': entry.get('title', 'Unknown Title'),
                        'url': url,
                        'thumbnail': entry.get('thumbnail', None),
                        'duration': entry.get('duration', 0),
                        'view_count': entry.get('view_count', 0)
                    })
            
            # If extract_info directly returns one video instead of a search list
            elif info.get('url') or info.get('webpage_url'):
                url = info.get('url') or info.get('webpage_url') or ""
                if url and not url.startswith('ytsearch') and info.get('_type') != 'url':
                    logger.info("Search returned a single video directly")
                    results.append({
                        'title': info.get('title', 'Unknown Title'),
                        'url': url,
                        'thumbnail': info.get('thumbnail', None),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0)
                    })

            if not results:
                logger.warning(f"No valid results found for '{search_query}'. info entries count: {len(info.get('entries', [])) if 'entries' in info else 'N/A'}")
                raise ValueError("No video results found via search API. Check if IP is blocked or proxy is failing.")
            
            logger.info(f"✅ Successfully extracted {len(results)} valid results")
            return results

    except Exception as e:
        logger.warning(f"Search failed: {e}. Attempting fallback with generic client and no extract_flat...")
        # Fallback 1: Try without extract_flat to get full entries (slower but more robust)
        ydl_opts['extract_flat'] = False
        ydl_opts['http_headers']['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                results = []
                entries = info.get('entries', [])
                for entry in entries:
                    if not entry: continue
                    url = entry.get('webpage_url') or entry.get('url') or ""
                    if url and not url.startswith('ytsearch'):
                        results.append({
                            'title': entry.get('title', 'Unknown Title'),
                            'url': url,
                            'thumbnail': entry.get('thumbnail', None),
                            'duration': entry.get('duration', 0),
                            'view_count': entry.get('view_count', 0)
                        })
                if not results:
                    raise ValueError("No results found on non-flat fallback.")
                return results
        except Exception as e2:
            logger.warning(f"Fallback 1 failed: {e2}. Trying basic URL search...")
            # Fallback 2: If everything fails, return an informative error for the UI
            raise RuntimeError(f"Video search is currently unavailable from this server's IP. Please try providing a direct YouTube URL instead. Details: {str(e)}")


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
    if "youtube.com" in url or "youtu.be" in url or "vimeo.com" in url:
        ydl_opts = get_ydl_opts({'format': 'best[ext=mp4]/best'})
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_url = info['url']
        except Exception:
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
    
    # Get headers from yt-dlp to pass to ffmpeg
    headers = ""
    if any(domain in video_url for domain in ["youtube.com", "youtu.be", "googlevideo.com", "v.redd.it"]):
        ydl_opts = get_ydl_opts()
        user_agent = ydl_opts['http_headers']['User-Agent']
        headers = f"User-Agent: {user_agent}\r\n"
        
    try:
        # Pass headers to ffmpeg to avoid 403 Forbidden
        input_args = {}
        if headers:
            input_args['headers'] = headers

        out, _ = (
            ffmpeg
            .input(video_url, ss=timestamp, **input_args)
            .output('pipe:', vframes=1, format='image2', vcodec='png')
            .run(capture_stdout=True, capture_stderr=True)
        )
        image = Image.open(io.BytesIO(out))
        return np.array(image)
    except ffmpeg.Error as e:
        raise RuntimeError(f"ffmpeg error: {e.stderr.decode('utf8')}")
    except Exception as e:
        raise RuntimeError(f"Frame extraction failed: {str(e)}")

def extract_multiple_frames_from_url(url: str, target_samples: int = 5) -> list[np.ndarray]:
    """
    Extracts frames, filters out bad ones (dark/blurry), and returns the best target_samples.
    """
    ydl_opts = get_ydl_opts({'format': 'best[ext=mp4]/best'})
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info['url']
            duration = info.get('duration', 60)
    except Exception:
        ydl_opts['extractor_args']['youtube']['player_client'] = ['android']
        ydl_opts['http_headers']['User-Agent'] = 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip'
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_url = info['url']
                duration = info.get('duration', 60)
        except Exception as e2:
             raise RuntimeError(f"Failed to extract video URL: {str(e2)}")

    valid_frames = []
    attempts = 0
    max_attempts = target_samples * 4 # Try 4x as many timestamps as needed
    
    if duration < 5: duration = 5
    
    # Generate more timestamps than needed to allow for filtering
    timestamps = sorted([random.uniform(duration * 0.1, duration * 0.9) for _ in range(max_attempts)])
    
    for ts in timestamps:
        try:
            frame = extract_frame_from_url(video_url, ts)
            if is_frame_useful(frame):
                valid_frames.append(frame)
                logger.info(f"✅ Accepted frame at {ts}s")
            else:
                logger.info(f"❌ Rejected frame at {ts}s (dark/blurry)")
                
            if len(valid_frames) >= target_samples:
                break
        except Exception as e:
            logger.warning(f"Failed to extract frame at {ts}: {e}")

    if not valid_frames:
        # If strict filtering rejected everything, try relaxed filtering or just take whatever we got
        raise ValueError("Could not extract any useful frames (video might be too dark)")
        
    return valid_frames[:target_samples]

# --- Color Science Functions ---
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
    frames = extract_multiple_frames_from_url(video_url, target_samples=5)
    avg_mean, avg_std = get_aggregated_lab_stats(frames)
    identity = generate_identity_lut(33)
    transformed_lut = apply_color_transfer(identity, avg_mean, avg_std)
    write_cube_file(transformed_lut, output_lut_path, 33)
    # Save first frame as preview
    Image.fromarray(frames[0]).save(output_frame_path)
