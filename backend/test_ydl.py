from dotenv import load_dotenv
import os
import yt_dlp

load_dotenv()

opts = {
    'quiet': False,
    'default_search': 'ytsearch5:',
    'extract_flat': True,
    'http_headers': {
        'User-Agent': 'com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    },
    'extractor_args': {
        'youtube': {'player_client': ['ios', 'android', 'mweb']}
    }
}
proxy_ip = os.getenv('proxy-ip')
proxy_user = os.getenv('username')
proxy_pass = os.getenv('password')
proxy_port = os.getenv('http-port')

if proxy_ip and proxy_port:
    opts['proxy'] = f"http://{proxy_user}:{proxy_pass}@{proxy_ip}:{proxy_port}"
    print(f"Using proxy: {opts['proxy']}")

with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info("ytsearch1:Dune trailer", download=False)
    print(info)
