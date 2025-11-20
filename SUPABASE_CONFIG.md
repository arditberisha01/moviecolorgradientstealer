# Supabase Configuration Guide

## Storage Bucket Setup

### 1. Create Storage Bucket

1. Go to your Supabase Dashboard: https://app.supabase.com
2. Select your project: `hhxtlrdtopezduyqwvld`
3. Navigate to **Storage** in the left sidebar
4. Click **New bucket**
5. Configure:
   - **Name**: `color-stealer`
   - **Public bucket**: ✅ **Yes** (required for public file access)
   - **File size limit**: **500 MB** (increased from default 50MB)
   - **Allowed MIME types**: Leave empty (allow all) or specify:
     - `video/*`
     - `image/*`
     - `application/octet-stream`

### 2. Update File Size Limit

If your bucket already exists:

1. Go to **Storage** → Select `color-stealer` bucket
2. Click **Settings** (gear icon)
3. Update **File size limit** to **500 MB** (524,288,000 bytes)
4. Click **Save**

### 3. Get API Credentials

1. Go to **Settings** → **API**
2. Copy these values:

```bash
# Project URL
SUPABASE_URL=https://hhxtlrdtopezduyqwvld.supabase.co

# anon public key (NOT service_role!)
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Bucket name
SUPABASE_BUCKET=color-stealer
```

⚠️ **IMPORTANT**: Use the **`anon` `public`** key, NOT the `service_role` secret key!

### 4. Set Environment Variables

#### For Render Backend:

Go to your Render backend service → **Environment** tab:

```bash
SUPABASE_URL=https://hhxtlrdtopezduyqwvld.supabase.co
SUPABASE_KEY=your_anon_public_key_here
SUPABASE_BUCKET=color-stealer
DATA_DIR=/tmp/data
```

#### For Local Development:

Create `backend/.env`:

```bash
SUPABASE_URL=https://hhxtlrdtopezduyqwvld.supabase.co
SUPABASE_KEY=your_anon_public_key_here
SUPABASE_BUCKET=color-stealer
DATA_DIR=./data
```

### 5. Verify Bucket Policies

Make sure your bucket has public read access:

1. Go to **Storage** → `color-stealer` → **Policies**
2. Ensure there's a policy allowing public SELECT (read) access
3. If not, create one:

```sql
CREATE POLICY "Public Access"
ON storage.objects FOR SELECT
USING ( bucket_id = 'color-stealer' );
```

### 6. Auto-Cleanup Feature

The platform automatically deletes all old files before uploading new ones to stay within the 1GB free tier limit.

**How it works:**
- Before each upload, `storage_manager.delete_all_files_in_bucket()` is called
- All files in the bucket are listed
- All files are deleted in a batch operation
- New files are then uploaded

**Free Tier Limits:**
- Storage: 1 GB
- Bandwidth: 2 GB/month
- API requests: 50,000/month

With auto-cleanup, you'll never exceed the storage limit!

---

## Troubleshooting

### "Failed to upload to Supabase"

**Check:**
1. Is `SUPABASE_URL` correct?
2. Is `SUPABASE_KEY` the **anon public** key (not service_role)?
3. Does the bucket `color-stealer` exist?
4. Is the bucket set to **Public**?
5. Is the file size limit set to 500MB?

### "File too large"

**Backend limit:** 500MB (configured in `endpoints.py`)
**Supabase limit:** Must be set to 500MB in bucket settings

If you get this error:
1. Check Supabase bucket file size limit
2. Verify the file is under 500MB
3. Check Render service logs for details

### "Access denied" or "Unauthorized"

**Possible causes:**
1. Using `service_role` key instead of `anon` key
2. Bucket is not set to public
3. Missing bucket policies

**Fix:**
1. Use the **anon public** key
2. Set bucket to public
3. Add public read policy (see step 5 above)

---

## Testing

### Test Upload (Local)

```bash
# Start Docker containers
docker compose up

# Upload a test video
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test_video.mp4"

# Check Supabase dashboard to verify file appears
```

### Test Upload (Production)

```bash
# Upload via frontend
# Go to: https://color-stealer-frontend.onrender.com
# Upload a video file
# Check Supabase dashboard to verify file appears
```

---

## Current Configuration

**Project:** `hhxtlrdtopezduyqwvld`  
**Bucket:** `color-stealer`  
**Max File Size:** 500 MB  
**Public Access:** ✅ Enabled  
**Auto-Cleanup:** ✅ Enabled  
**Free Tier:** 1 GB storage, 2 GB bandwidth/month

