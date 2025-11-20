# Deployment

## Render

This project is configured for deployment on [Render](https://render.com).

### Backend Deployment (Web Service)

1. **Create a new Web Service** on Render
2. **Connect your GitHub repository**: `https://github.com/arditberisha01/moviecolorgradientstealer`
3. **Configuration**:
   - **Name**: `color-stealer-backend`
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. **Environment Variables**:
   ```
   SUPABASE_URL=https://hhxtlrdtopezduyqwvld.supabase.co
   SUPABASE_KEY=your_supabase_anon_key
   SUPABASE_BUCKET=color-stealer
   DATA_DIR=/tmp/data
   ```

### Frontend Deployment (Static Site)

1. **Create a new Static Site** on Render
2. **Connect your GitHub repository**
3. **Configuration**:
   - **Name**: `color-stealer-frontend`
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`

4. **Environment Variables**:
   ```
   VITE_API_URL=https://color-stealer-backend.onrender.com
   ```

### Notes

- **Free Plan**: Backend will spin down after 15 minutes of inactivity (first request may be slow)
- **Supabase Storage**: Automatically cleans up old files to stay within 1GB free tier
- **Persistent Storage**: Use `/tmp` on Render (ephemeral, resets on deploy)

## Local Development

See main [README.md](../README.md) for local setup instructions.

