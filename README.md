# Video Color Grade Stealer

A web platform that extracts color grading from videos and generates downloadable `.cube` LUT files.

## Features

- **Upload Video**: Analyze local video files
- **URL Analysis**: Paste YouTube/Vimeo links for instant analysis
- **Movie Search**: Type a movie name to analyze its trailer's color grade
- **Multi-frame Sampling**: Aggregates color stats from multiple frames for accurate LUTs
- **Cloud Storage**: Integrated with Supabase for scalable file storage (with auto-cleanup for free tier)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Supabase account for cloud storage

### Local Development

1. **Clone the repository:**
```bash
git clone https://github.com/arditberisha01/moviecolorgradientstealer.git
cd moviecolorgradientstealer
```

2. **Configure Supabase (Optional):**
```bash
cp backend/.env.example backend/.env
# Edit backend/.env and add your Supabase credentials
```

3. **Start the application:**
```bash
docker compose up --build
```

4. **Access the app:**
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/docs`

## Environment Variables

Create a `backend/.env` file with:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_BUCKET=color-stealer
DATA_DIR=/data
```

If Supabase credentials are not provided, the app will use local file storage.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on deploying to Render.

## Tech Stack

**Backend:**
- FastAPI
- OpenCV & FFmpeg
- yt-dlp (YouTube/Vimeo support)
- Supabase Storage (with auto-cleanup for 1GB free tier)

**Frontend:**
- React + TypeScript
- Vite
- Tailwind CSS
- ReactPlayer

## How It Works

1. **Frame Extraction**: Uses FFmpeg/OpenCV to extract frames from videos
2. **Color Analysis**: Converts frames to LAB color space and calculates mean/std dev
3. **LUT Generation**: Applies Reinhard color transfer to a 3D identity LUT
4. **Output**: Generates standard `.cube` files compatible with Premiere Pro, DaVinci Resolve, Final Cut Pro
5. **Auto-Cleanup**: Automatically deletes old files from Supabase to stay within 1GB free tier

## License

MIT
