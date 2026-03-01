"""
Cobalt API client for downloading videos from multiple platforms.
Supports YouTube, Instagram, TikTok, Twitter/X, Reddit, Vimeo, and more.
See: https://github.com/imputnet/cobalt
"""

import httpx
import os
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cobalt API instances, ordered by reliability
COBALT_INSTANCES = [
    "https://cobalt-api.meowing.de",
    "https://cobalt-backend.canine.tools",
    "https://kityune.imput.net",
]

DATA_DIR = os.getenv("DATA_DIR", "data")
DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _get_cobalt_url() -> str:
    """Get the configured Cobalt API URL, or fall back to defaults."""
    return os.getenv("COBALT_API_URL", COBALT_INSTANCES[0])


def _get_all_instances() -> list[str]:
    """Return all instance URLs to try, custom first if set."""
    custom = os.getenv("COBALT_API_URL")
    if custom:
        return [custom] + [u for u in COBALT_INSTANCES if u != custom]
    return list(COBALT_INSTANCES)


async def download_video(
    url: str,
    quality: str = "1080",
    download_mode: str = "auto",
    timeout: float = 120.0,
) -> str:
    """
    Download a video from any Cobalt-supported platform.

    Args:
        url: The source URL (YouTube, Instagram, TikTok, Twitter, etc.)
        quality: Video quality — max/2160/1440/1080/720/480/360/240/144
        download_mode: auto (video+audio), audio (audio only), mute (video only)
        timeout: Request timeout in seconds

    Returns:
        Local file path to the downloaded video.

    Raises:
        RuntimeError on failure.
    """
    instances = _get_all_instances()
    last_error = None

    for instance_url in instances:
        try:
            return await _try_download(instance_url, url, quality, download_mode, timeout)
        except Exception as e:
            logger.warning(f"Cobalt instance {instance_url} failed: {e}")
            last_error = e
            continue

    raise RuntimeError(
        f"All Cobalt instances failed for URL: {url}. Last error: {last_error}"
    )


async def _try_download(
    instance_url: str,
    source_url: str,
    quality: str,
    download_mode: str,
    timeout: float,
) -> str:
    """Attempt to download via a specific Cobalt instance."""
    payload = {
        "url": source_url,
        "videoQuality": quality,
        "downloadMode": download_mode,
        "filenameStyle": "basic",
        "youtubeVideoCodec": "h264",
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Add API key if configured for this instance
    api_key = os.getenv("COBALT_API_KEY")
    if api_key:
        headers["Authorization"] = f"Api-Key {api_key}"

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        logger.info(f"🔗 Requesting Cobalt: {instance_url} for URL: {source_url}")

        resp = await client.post(instance_url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status")

        if status == "error":
            error_info = data.get("error", {})
            code = error_info.get("code", "unknown")
            raise RuntimeError(f"Cobalt error: {code}")

        if status == "redirect":
            # Direct URL — download it
            download_url = data["url"]
            filename = data.get("filename", f"{uuid.uuid4()}.mp4")
            return await _download_file(client, download_url, filename)

        if status == "tunnel":
            # Cobalt proxied URL — download it
            download_url = data["url"]
            filename = data.get("filename", f"{uuid.uuid4()}.mp4")
            return await _download_file(client, download_url, filename)

        if status == "picker":
            # Multiple items (e.g., Instagram carousel) — pick first video
            picker_items = data.get("picker", [])
            video_items = [p for p in picker_items if p.get("type") == "video"]
            if not video_items:
                # Fall back to any item
                video_items = picker_items

            if not video_items:
                raise RuntimeError("Cobalt picker returned no downloadable items")

            item = video_items[0]
            download_url = item["url"]
            filename = f"{uuid.uuid4()}.mp4"
            return await _download_file(client, download_url, filename)

        if status == "local-processing":
            # Files need local remuxing — download the tunnel URLs
            tunnels = data.get("tunnel", [])
            if not tunnels:
                raise RuntimeError("Cobalt local-processing returned no tunnels")
            # Download first tunnel (usually the video stream)
            download_url = tunnels[0]
            filename = f"{uuid.uuid4()}.mp4"
            return await _download_file(client, download_url, filename)

        raise RuntimeError(f"Unexpected Cobalt response status: {status}")


async def _download_file(client: httpx.AsyncClient, url: str, filename: str) -> str:
    """Download a file from a URL to the local download directory."""
    local_path = os.path.join(DOWNLOAD_DIR, filename)

    logger.info(f"⬇️  Downloading: {filename}")

    async with client.stream("GET", url) as resp:
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            async for chunk in resp.aiter_bytes(chunk_size=65536):
                f.write(chunk)

    file_size = os.path.getsize(local_path)
    logger.info(f"✅ Downloaded {filename} ({file_size / 1024 / 1024:.1f} MB)")

    return local_path


async def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    """
    Search YouTube for videos matching the query.
    Uses Cobalt-compatible approach: construct YouTube search URLs
    and extract info. Falls back to YouTube oEmbed for metadata.

    Returns list of dicts with: title, url, thumbnail, duration
    """
    # We use a lightweight approach: scrape YouTube search results
    # via the InnerTube API (same as used by youtube.com frontend)
    search_url = "https://www.youtube.com/results"
    params = {"search_query": f"{query} official trailer"}

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        }
        resp = await client.get(search_url, params=params, headers=headers)
        resp.raise_for_status()
        html = resp.text

    # Parse video IDs from the response
    import re
    video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
    # Deduplicate while preserving order
    seen = set()
    unique_ids = []
    for vid in video_ids:
        if vid not in seen:
            seen.add(vid)
            unique_ids.append(vid)
        if len(unique_ids) >= max_results:
            break

    if not unique_ids:
        raise RuntimeError(f"No YouTube results found for: {query}")

    # Get metadata for each video via oEmbed
    results = []
    for vid_id in unique_ids:
        video_url = f"https://www.youtube.com/watch?v={vid_id}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                oembed_resp = await client.get(
                    "https://www.youtube.com/oembed",
                    params={"url": video_url, "format": "json"},
                )
                if oembed_resp.status_code == 200:
                    oembed = oembed_resp.json()
                    results.append({
                        "title": oembed.get("title", "Unknown Title"),
                        "url": video_url,
                        "thumbnail": oembed.get("thumbnail_url", f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg"),
                        "duration": 0,  # oEmbed doesn't provide duration
                    })
                else:
                    results.append({
                        "title": "Unknown Title",
                        "url": video_url,
                        "thumbnail": f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg",
                        "duration": 0,
                    })
        except Exception as e:
            logger.warning(f"Failed to get oEmbed for {vid_id}: {e}")
            results.append({
                "title": "Unknown Title",
                "url": video_url,
                "thumbnail": f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg",
                "duration": 0,
            })

    return results


def cleanup_download(file_path: str):
    """Remove a downloaded file after processing."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"🗑️  Cleaned up: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to clean up {file_path}: {e}")
