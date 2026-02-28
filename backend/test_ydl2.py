import yt_dlp

opts = {
    'quiet': False,
    'default_search': 'ytsearch5:',
    'extract_flat': True,
}

with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info("ytsearch1:Dune trailer", download=False)
    print("Entries:", len(info.get('entries', [])))
