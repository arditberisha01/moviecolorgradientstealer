# Color Stealer - Complete Project Summary

## 🎬 Project Overview

**Color Stealer** is a SaaS platform that extracts color grades from videos and generates downloadable `.cube` LUT files. Users can upload videos, paste YouTube/Vimeo URLs, or search for movies to analyze their cinematic color grading.

**Live URLs:**
- Frontend: `https://color-stealer-frontend.onrender.com`
- Backend: `https://color-stealer-backend.onrender.com`
- GitHub: `https://github.com/arditberisha01/moviecolorgradientstealer.git`

---

## 🏗️ Architecture

### Tech Stack

**Backend:**
- FastAPI (Python web framework)
- FFmpeg (video processing)
- OpenCV (frame extraction & image processing)
- yt-dlp (YouTube/Vimeo video downloading)
- Supabase Storage (cloud file storage)
- Deployed on Render (Web Service)

**Frontend:**
- React + TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- ReactPlayer (video playback)
- Axios (HTTP client)
- Deployed on Render (Web Service)

**Infrastructure:**
- Docker & Docker Compose (local development)
- Supabase (1GB free storage with auto-cleanup)
- Render (cloud deployment platform)

---

## ✨ Features Implemented

### 1. **Upload Video File**
- Drag & drop or click to upload video files
- Real-time video preview with ReactPlayer
- Pause at any frame and extract color grade
- **Optimized Performance**: Uploads process locally first, skipping heavy video upload to cloud

### 2. **Paste URL (YouTube/Vimeo)**
- Paste any YouTube or Vimeo link
- Stream video directly in browser
- Select timestamp and extract color grade
- Backend downloads and processes the video frame

### 3. **Movie Search**
- Enter a movie name (e.g., "Dune", "Blade Runner 2049")
- Platform searches YouTube for official trailer
- Extracts **5 random frames** from different timestamps
- **Smart Filtering**: Automatically rejects dark, blurry, or low-quality frames
- Aggregates color statistics for comprehensive LUT
- More accurate representation of the movie's overall look

### 4. **LUT Generation**
- Uses **Reinhard's Color Transfer Algorithm**
- Analyzes color statistics in LAB color space
- Generates industry-standard `.cube` files
- Compatible with:
  - Adobe Premiere Pro (Lumetri Color)
  - DaVinci Resolve
  - Final Cut Pro
  - Any software supporting 3D LUTs

### 5. **Supabase Storage Integration**
- Automatic file upload to Supabase
- Public URL generation for downloads
- **Auto-cleanup**: Deletes all old files before new uploads
- Stays within 1GB free tier limit

---

## 📁 Project Structure

```
/Users/arditberisha/gonnyfittzideashumesmutmecursoreprovojna/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── api/
│   │   │   └── endpoints.py        # API routes
│   │   └── core/
│   │       ├── lut_generator.py    # Core LUT generation logic
│   │       └── storage.py          # Supabase storage manager
│   ├── Dockerfile                  # Backend container config
│   ├── requirements.txt            # Python dependencies
│   ├── Procfile                    # Render deployment config
│   └── .env.example                # Environment variables template
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # Main React component
│   │   └── main.tsx                # React entry point
│   ├── Dockerfile                  # Frontend container config
│   ├── package.json                # Node dependencies
│   ├── vite.config.ts              # Vite configuration
│   └── tailwind.config.js          # Tailwind CSS config
├── docker-compose.yml              # Local development orchestration
├── README.md                       # Project documentation
├── DEPLOYMENT.md                   # Render deployment guide
└── PROJECT_SUMMARY.md              # This file
```

---

## 🔧 Technical Implementation Details

### Backend API Endpoints

#### 1. `POST /api/generate-from-image`
- Accepts: Image file (captured frame from browser)
- Returns: LUT URL and frame preview URL
- Process:
  1. Receives image blob
  2. Analyzes color statistics in LAB space
  3. Generates identity LUT and applies color transfer
  4. Uploads to Supabase
  5. Returns public URLs

#### 2. `POST /api/generate-from-url`
- Accepts: `{ url: string, timestamp: number }`
- Returns: LUT URL and frame preview URL
- Process:
  1. Uses `yt-dlp` to resolve video URL
  2. Uses `ffmpeg` to extract frame at timestamp
  3. Generates LUT from extracted frame
  4. Uploads to Supabase
  5. Returns public URLs

#### 3. `POST /api/analyze-movie`
- Accepts: `{ query: string }`
- Returns: LUT URL and frame preview URL
- Process:
  1. Searches YouTube for "{query} official trailer 4k"
  2. Extracts 5 random frames (10%-90% of video duration)
  3. **Smart Filtering**: Analyzes brightness/variance to reject bad frames
  4. Calculates aggregated color statistics
  5. Generates comprehensive LUT
  6. Uploads to Supabase
  7. Returns public URLs

#### 4. `GET /api/download/generated/{filename}`
- Serves generated files (LUTs and frames)
- Redirects to Supabase public URL if available
- Falls back to local file system

### Core Algorithm: Color Transfer

**File:** `backend/app/core/lut_generator.py`

**Method:** Reinhard's Color Transfer in LAB Space

1. **Extract Frame**: Use FFmpeg/OpenCV to get video frame
2. **Convert to LAB**: Transform RGB → LAB color space
3. **Calculate Statistics**: Mean and standard deviation for L, A, B channels
4. **Generate Identity LUT**: Create neutral 33×33×33 RGB grid
5. **Apply Transfer**: 
   ```python
   for each channel in [L, A, B]:
       channel = (channel - source_mean) / source_std
       channel = channel * target_std + target_mean
   ```
6. **Convert Back**: LAB → RGB
7. **Write .cube File**: Standard format with 33³ = 35,937 entries

### YouTube Bot Bypass

**Problem:** YouTube blocks `yt-dlp` with "Sign in to confirm you're not a bot"

**Solution:** Implemented in all `yt-dlp` calls:
```python
ydl_opts = {
    'format': 'best[ext=mp4]/best',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],  # Use Android client
            'skip': ['hls', 'dash']
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 ...',
        'Accept': 'text/html,application/xhtml+xml,...',
        'Accept-Language': 'en-us,en;q=0.5',
        'Sec-Fetch-Mode': 'navigate',
    },
    'socket_timeout': 30
}
```

### Frontend ReactPlayer Integration

**Challenges Solved:**
1. **`getInternalPlayer()` not available**: Added fallback methods
2. **`getCurrentTime()` errors**: Added null checks and try-catch
3. **Video not loaded**: Added validation for `videoWidth` before capture

**Implementation:**
```typescript
// Flexible internal player access
let internalPlayer: HTMLVideoElement | null = null

if (typeof playerRef.current.getInternalPlayer === 'function') {
  internalPlayer = playerRef.current.getInternalPlayer()
} else if (playerRef.current.player && playerRef.current.player.player) {
  internalPlayer = playerRef.current.player.player
}

// Validate before capture
if (!internalPlayer || !internalPlayer.videoWidth) {
   throw new Error("Video not ready. Please wait...")
}
```

### Supabase Auto-Cleanup

**File:** `backend/app/core/storage.py`

**Implementation:**
```python
async def delete_all_files_in_bucket(self):
    if self.supabase:
        files = self.supabase.storage.from_(self.supabase_bucket).list()
        file_names = [f['name'] for f in files if f['name'] not in ['.', '..']]
        
        if file_names:
            self.supabase.storage.from_(self.supabase_bucket).remove(file_names)
            logging.info(f"Deleted {len(file_names)} files")
```

Called before every new upload to stay within 1GB free tier.

---

## 🐛 Issues Fixed

### 1. **Docker Compose Syntax**
- **Error:** `command not found: docker-compose`
- **Fix:** Changed to `docker compose` (modern CLI)

### 2. **Port Conflicts**
- **Error:** `port 8000 already allocated`
- **Fix:** Stopped old containers, used `docker compose start` to reuse

### 3. **Missing FFmpeg**
- **Error:** `command not found: ffmpeg`
- **Fix:** Added `apt-get install -y ffmpeg` to Dockerfile

### 4. **Frontend Build Errors**
- **Error:** `failed to read dockerfile`
- **Fix:** Created missing `frontend/Dockerfile`

### 5. **ReactPlayer TypeScript Errors**
- **Error:** `'ReactPlayer' refers to a value, but is being used as a type`
- **Fix:** Changed `useRef<ReactPlayer>` to `useRef<any>`

### 6. **Vite Blocked Host**
- **Error:** `This host ("color-stealer-frontend.onrender.com") is not allowed`
- **Fix:** Added `allowedHosts: ['.onrender.com', 'localhost']` to `vite.config.ts`

### 7. **ReactPlayer Internal Access**
- **Error:** `getInternalPlayer is not a function`
- **Fix:** Added fallback methods and validation

### 8. **URL Processing Timeout**
- **Error:** Request hangs forever
- **Fix:** Added 60s timeout to axios, 30s to yt-dlp socket

### 9. **FFmpeg Timeout Parameter**
- **Error:** `run() got an unexpected keyword argument 'timeout'`
- **Fix:** Removed unsupported `timeout` parameter from `ffmpeg.run()`

### 10. **YouTube Bot Detection**
- **Error:** `Sign in to confirm you're not a bot`
- **Fix:** Implemented user-agent spoofing + Android client

### 11. **GitHub Push Failures**
- **Error:** Large files exceeding limits
- **Fix:** Added `venv/` and `data/` to `.gitignore`

---

## 🚀 Deployment Configuration

### Render - Backend (Web Service)

**Settings:**
- **Name:** `color-stealer-backend`
- **Runtime:** Python 3
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Root Directory:** `backend`

**Environment Variables:**
```bash
SUPABASE_URL=https://hhxtlrdtopezduyqwvld.supabase.co
SUPABASE_KEY=your_anon_public_key  # NOT service_role key!
SUPABASE_BUCKET=color-stealer
DATA_DIR=/tmp/data
```

### Render - Frontend (Web Service)

**Settings:**
- **Name:** `color-stealer-frontend`
- **Runtime:** Node
- **Build Command:** `npm install`
- **Start Command:** `npm run dev -- --host 0.0.0.0 --port $PORT`
- **Root Directory:** `frontend`

**Environment Variables:**
```bash
VITE_API_URL=https://color-stealer-backend.onrender.com
```

### Vite Configuration

**File:** `frontend/vite.config.ts`

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: process.env.PORT ? parseInt(process.env.PORT) : 5173,
    strictPort: false,
    allowedHosts: [
      'color-stealer-frontend.onrender.com',
      '.onrender.com',
      'localhost'
    ],
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://backend:8000',
        changeOrigin: true,
      }
    }
  }
})
```

---

## 📦 Dependencies

### Backend (`requirements.txt`)
```
fastapi
uvicorn
python-multipart
numpy
pillow
opencv-python-headless
scikit-image
scipy
yt-dlp
ffmpeg-python
python-dotenv
supabase
```

### Frontend (`package.json`)
```json
{
  "dependencies": {
    "axios": "^1.4.0",
    "clsx": "^2.0.0",
    "lucide-react": "^0.263.1",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-player": "^3.4.0",
    "tailwind-merge": "^1.14.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.15",
    "@types/react-dom": "^18.2.7",
    "@vitejs/plugin-react": "^4.0.3",
    "autoprefixer": "^10.4.14",
    "postcss": "^8.4.27",
    "tailwindcss": "^3.3.3",
    "typescript": "^5.0.2",
    "vite": "^4.4.5"
  }
}
```

---

## 🔐 Supabase Setup

### Storage Bucket Configuration

1. **Create Bucket:**
   - Name: `color-stealer`
   - Public: ✅ Yes
   - File size limit: Default
   - Allowed MIME types: All

2. **Get Credentials:**
   - Go to **Settings** → **API**
   - Copy **Project URL** → `SUPABASE_URL`
   - Copy **anon public** key → `SUPABASE_KEY`
   - ⚠️ **DO NOT** use `service_role` key!

3. **Auto-Cleanup:**
   - Implemented in `backend/app/core/storage.py`
   - Deletes all files before new upload
   - Keeps storage under 1GB free tier

---

## 🧪 Local Development

### Prerequisites
- Docker & Docker Desktop
- Git

### Setup
```bash
# Clone repository
git clone https://github.com/arditberisha01/moviecolorgradientstealer.git
cd moviecolorgradientstealer

# Create backend .env file
cd backend
cp .env.example .env
# Edit .env with your Supabase credentials

# Start services
cd ..
docker compose up --build

# Access application
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
```

### Useful Commands
```bash
# Start existing containers
docker compose start

# Stop containers
docker compose stop

# View logs
docker compose logs -f

# Rebuild specific service
docker compose up --build backend
docker compose up --build frontend

# Remove containers
docker compose down
```

---

## 🎨 UI/UX Features

### Design System
- **Color Palette:**
  - Background: `slate-950` (dark)
  - Cards: `slate-900/50` (semi-transparent)
  - Primary: `indigo-600` (buttons)
  - Accent: `cyan-400` (highlights)
  - Text: `slate-100` (light)

- **Typography:**
  - Headings: Gradient text (indigo → cyan)
  - Body: `slate-400`
  - Interactive: Hover transitions

- **Components:**
  - Rounded corners: `rounded-xl`, `rounded-2xl`
  - Borders: `border-slate-800`
  - Shadows: `shadow-lg`, `shadow-2xl`
  - Animations: Fade-in, slide-in

### User Flow
1. **Landing:** See three tabs (Upload, URL, Movie)
2. **Select Mode:** Choose input method
3. **Input:** Upload file / paste URL / search movie
4. **Preview:** See video player (for upload/URL modes)
5. **Action:** Click "Steal Grade" button
6. **Processing:** Loading spinner with status
7. **Result:** Preview frame + Download .cube button

---

## 📊 Performance Considerations

### Timeouts
- Frontend → Backend: 60s (URL), 90s (Movie)
- yt-dlp socket: 30s
- Frontend handles timeout gracefully

### File Sizes
- Supabase: Auto-cleanup keeps under 1GB
- Local Docker: Volumes persist in `./backend/data/`
- Render: Uses `/tmp/data` (ephemeral)

### Optimization Opportunities (Future)
- Cache YouTube video URLs (avoid re-downloading)
- WebSocket for real-time progress updates
- Client-side LUT preview before download
- Batch processing for multiple videos

---

## 🔮 Future Enhancements (Not Implemented)

1. **User Accounts & History**
   - Save generated LUTs
   - Browse past extractions
   - Favorites/collections

2. **Advanced LUT Options**
   - Adjustable LUT size (17, 33, 65)
   - Intensity slider (0-100%)
   - Multiple color transfer algorithms

3. **Batch Processing**
   - Upload multiple videos
   - Generate LUT pack

4. **Social Features**
   - Share LUTs with community
   - Browse popular movie grades
   - Rate and review

5. **Premium Features**
   - Higher resolution frame extraction
   - Longer video support
   - Priority processing queue

---

## 📝 Git Commit History (Key Milestones)

1. Initial project scaffold with Docker Compose
2. Backend API implementation with FFmpeg
3. Frontend React UI with Tailwind
4. ReactPlayer integration for video playback
5. YouTube/Vimeo URL support with yt-dlp
6. Movie search with multi-frame analysis
7. Supabase Storage integration
8. Auto-cleanup for 1GB free tier
9. Render deployment configuration
10. YouTube bot bypass implementation
11. ReactPlayer error fixes
12. URL processing timeout fixes
13. FFmpeg timeout parameter fix
14. **Optimized Uploads**: Skip Supabase video upload for faster processing
15. **Smart Filtering**: Automatically reject dark/blurry frames for better LUTs

---

## 🆘 Troubleshooting

### "Video not ready" error
- **Cause:** Trying to capture before video loads
- **Fix:** Wait for video to fully load (see player controls)

### "Request timed out"
- **Cause:** Video too long or slow connection
- **Fix:** Try shorter video or check internet connection

### "Failed to analyze movie"
- **Cause:** YouTube blocking or trailer not found
- **Fix:** Try different movie name or use direct URL instead

### Supabase upload fails
- **Cause:** Wrong API key or bucket name
- **Fix:** Verify `SUPABASE_KEY` is **anon public** key, not service_role

### Frontend shows blank page
- **Cause:** Vite allowedHosts blocking
- **Fix:** Check `vite.config.ts` includes your domain

---

## 👨‍💻 Development Notes

### Key Learnings
1. ReactPlayer needs careful ref handling
2. yt-dlp requires bot bypass for YouTube
3. FFmpeg-python doesn't support timeout parameter
4. Supabase free tier needs active cleanup
5. Render requires specific Vite configuration

### Code Quality
- Type safety with TypeScript
- Error handling at all levels
- Graceful fallbacks for all features
- User-friendly error messages
- Responsive design (mobile-ready)

---

## 📄 License & Credits

**Project:** Color Stealer  
**Developer:** Ardit Berisha  
**Repository:** https://github.com/arditberisha01/moviecolorgradientstealer  
**Built with:** FastAPI, React, Docker, Supabase, Render  

**Algorithm Credits:**
- Reinhard's Color Transfer (2001)
- LAB color space transformation

---

## 🎯 Project Status: ✅ COMPLETE & DEPLOYED

**All features implemented and working:**
- ✅ Upload video files
- ✅ Paste YouTube/Vimeo URLs
- ✅ Search movies by name
- ✅ Generate .cube LUT files
- ✅ Supabase storage with auto-cleanup
- ✅ Deployed to Render
- ✅ Modern, responsive UI
- ✅ Error handling & timeouts
- ✅ YouTube bot bypass
- ✅ Optimized Upload Performance
- ✅ Smart Frame Filtering

**Ready for production use!** 🚀
