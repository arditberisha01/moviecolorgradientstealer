import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import ReactPlayer from 'react-player'
import { Upload, FileVideo, Download, Loader2, Image as ImageIcon, Link as LinkIcon, Youtube, Scissors, Search, Film } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Utility for tailwind class merging
function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs))
}

function App() {
  const [mode, setMode] = useState<'upload' | 'url' | 'movie'>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [fileUrl, setFileUrl] = useState<string | null>(null)
  const [url, setUrl] = useState<string>('')
  const [movieQuery, setMovieQuery] = useState<string>('')
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState<{ lut_url: string, frame_url: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const playerRef = useRef<any>(null)

  // Handle File Selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      setFile(selectedFile)
      setFileUrl(URL.createObjectURL(selectedFile))
      setError(null)
      setResult(null)
    }
  }

  // Cleanup object URL
  useEffect(() => {
    return () => {
      if (fileUrl) URL.revokeObjectURL(fileUrl)
    }
  }, [fileUrl])

  // Method 1: Capture from Local File (via ReactPlayer's internal video element)
  const handleCaptureFromFile = async () => {
    if (!file || !playerRef.current) return
    
    setProcessing(true)
    setError(null)

    try {
      // Access internal player to get the video element
      let internalPlayer: HTMLVideoElement | null = null
      
      // Try different methods to get the internal player
      if (typeof playerRef.current.getInternalPlayer === 'function') {
        internalPlayer = playerRef.current.getInternalPlayer() as HTMLVideoElement
      } else if (playerRef.current.player && playerRef.current.player.player) {
        internalPlayer = playerRef.current.player.player as HTMLVideoElement
      }
      
      if (!internalPlayer || !internalPlayer.videoWidth) {
         throw new Error("Video not ready. Please wait for the video to load and try again.")
      }

      // 1. Create Canvas & Draw Frame
      const canvas = document.createElement('canvas')
      canvas.width = internalPlayer.videoWidth
      canvas.height = internalPlayer.videoHeight
      const ctx = canvas.getContext('2d')
      if (!ctx) throw new Error("Could not create canvas context")
      
      ctx.drawImage(internalPlayer, 0, 0, canvas.width, canvas.height)
      
      // 2. Convert to Blob
      canvas.toBlob(async (blob) => {
        if (!blob) {
          setError("Could not capture frame")
          setProcessing(false)
          return
        }
        
        // 3. Upload Image
        const formData = new FormData()
        formData.append('file', blob, 'captured_frame.jpg')
        
        try {
          const res = await axios.post('/api/generate-from-image', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          })
          setResult(res.data)
        } catch (err: any) {
          setError(err.response?.data?.detail || "Processing failed")
        } finally {
          setProcessing(false)
        }
      }, 'image/jpeg', 0.95)

    } catch (err: any) {
      console.error(err)
      setError(err.message)
      setProcessing(false)
    }
  }

  // Method 2: Capture from URL (Backend downloads & extracts)
  const handleCaptureFromUrl = async () => {
    if (!url) return
    
    setProcessing(true)
    setError(null)
    
    let currentTime = 0
    
    // Try to get current time from player, fallback to 0
    try {
      if (playerRef.current && typeof playerRef.current.getCurrentTime === 'function') {
        currentTime = playerRef.current.getCurrentTime() || 0
      }
    } catch (e) {
      console.warn("Could not get current time from player, using 0", e)
    }
    
    try {
      const res = await axios.post('/api/generate-from-url', {
        url: url,
        timestamp: currentTime
      }, {
        timeout: 60000 // 60 second timeout
      })
      setResult(res.data)
    } catch (err: any) {
      console.error(err)
      if (err.code === 'ECONNABORTED') {
        setError("Request timed out. The video might be too long or unavailable.")
      } else {
        setError(err.response?.data?.detail || "Processing failed")
      }
    } finally {
      setProcessing(false)
    }
  }

  // Method 3: Search Movie & Analyze
  const handleMovieSearch = async () => {
    if (!movieQuery) return
    
    setProcessing(true)
    setError(null)
    setResult(null)
    
    try {
      const res = await axios.post('/api/analyze-movie', {
        query: movieQuery
      }, {
        timeout: 90000 // 90 second timeout for movie analysis (multiple frames)
      })
      setResult(res.data)
    } catch (err: any) {
      console.error(err)
      if (err.code === 'ECONNABORTED') {
        setError("Request timed out. Try a different movie or check your connection.")
      } else {
        setError(err.response?.data?.detail || "Analysis failed")
      }
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-8">
      <div className="max-w-5xl mx-auto">
        
        {/* Header */}
        <div className="text-center mb-12 space-y-4">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
            Color Stealer
          </h1>
          <p className="text-slate-400 text-lg">
            Extract the color grade from any video clip into a .cube LUT.
          </p>
        </div>

        {/* Main Grid */}
        <div className="grid gap-8 lg:grid-cols-3">
          
          {/* Left Column: Input & Player (Spans 2 cols) */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Tabs */}
            <div className="flex p-1 bg-slate-900 rounded-xl border border-slate-800 w-fit">
              <button 
                onClick={() => { setMode('upload'); setResult(null); setError(null); }}
                className={cn(
                  "px-6 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2",
                  mode === 'upload' ? "bg-indigo-600 text-white shadow-lg" : "text-slate-400 hover:text-white"
                )}
              >
                <Upload className="w-4 h-4" /> Upload File
              </button>
              <button 
                onClick={() => { setMode('url'); setResult(null); setError(null); }}
                className={cn(
                  "px-6 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2",
                  mode === 'url' ? "bg-indigo-600 text-white shadow-lg" : "text-slate-400 hover:text-white"
                )}
              >
                <LinkIcon className="w-4 h-4" /> Paste URL
              </button>
              <button 
                onClick={() => { setMode('movie'); setResult(null); setError(null); }}
                className={cn(
                  "px-6 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2",
                  mode === 'movie' ? "bg-indigo-600 text-white shadow-lg" : "text-slate-400 hover:text-white"
                )}
              >
                <Film className="w-4 h-4" /> Movie Search
              </button>
            </div>

            {/* Input Area */}
            <div className="bg-slate-900/50 rounded-2xl p-6 border border-slate-800 min-h-[400px] flex flex-col">
              
              {mode === 'upload' ? (
                // UPLOAD MODE
                !file || !fileUrl ? (
                  <div 
                    className="flex-1 border-2 border-dashed border-slate-700 rounded-xl flex flex-col items-center justify-center gap-4 hover:bg-slate-900 hover:border-indigo-500/50 transition-colors cursor-pointer"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      className="hidden" 
                      accept="video/*" 
                      onChange={handleFileChange}
                    />
                    <div className="p-4 bg-slate-800 rounded-full">
                      <FileVideo className="w-8 h-8 text-indigo-400" />
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-medium">Drop video here</p>
                      <p className="text-sm text-slate-500">or click to browse</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col gap-4">
                     {/* ReactPlayer for Local File */}
                     <div className="relative bg-black rounded-xl overflow-hidden flex-1 flex items-center justify-center">
                        <ReactPlayer
                          ref={playerRef}
                          url={fileUrl}
                          controls
                          width="100%"
                          height="100%"
                          className="absolute top-0 left-0"
                        />
                     </div>
                     <div className="flex items-center justify-between">
                        <button 
                          onClick={() => { setFile(null); setFileUrl(null); }}
                          className="text-sm text-slate-400 hover:text-white underline"
                        >
                          Change File
                        </button>
                        <button
                          onClick={handleCaptureFromFile}
                          disabled={processing}
                          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-semibold flex items-center gap-2 disabled:opacity-50"
                        >
                          {processing ? <Loader2 className="w-4 h-4 animate-spin"/> : <Scissors className="w-4 h-4"/>}
                          Steal Grade from Frame
                        </button>
                     </div>
                  </div>
                )
              ) : mode === 'url' ? (
                // URL MODE
                <div className="flex-1 flex flex-col gap-4">
                  <div className="flex gap-2">
                    <input 
                      type="text" 
                      placeholder="Paste YouTube or Vimeo link..." 
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  
                  {url ? (
                     <div className="relative bg-black rounded-xl overflow-hidden flex-1 flex items-center justify-center">
                        <ReactPlayer 
                          ref={playerRef}
                          url={url}
                          controls
                          width="100%"
                          height="100%"
                          className="absolute top-0 left-0"
                        />
                     </div>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-slate-600">
                      <Youtube className="w-16 h-16 mb-4 opacity-20" />
                      <p>Enter a URL to load video</p>
                    </div>
                  )}
                  
                  {url && (
                    <div className="flex justify-end">
                      <button
                          onClick={handleCaptureFromUrl}
                          disabled={processing}
                          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-semibold flex items-center gap-2 disabled:opacity-50"
                        >
                          {processing ? <Loader2 className="w-4 h-4 animate-spin"/> : <Scissors className="w-4 h-4"/>}
                          Steal Grade from Current Time
                        </button>
                    </div>
                  )}
                </div>
              ) : (
                // MOVIE SEARCH MODE
                <div className="flex-1 flex flex-col gap-4">
                  <div className="flex flex-col items-center justify-center flex-1 text-center space-y-6">
                    <Film className="w-16 h-16 text-indigo-500 opacity-50" />
                    <h2 className="text-2xl font-semibold">Analyze a Movie Look</h2>
                    <p className="text-slate-400 max-w-md">
                      Enter a movie name (e.g., "Dune", "The Matrix"). We'll find the trailer, sample multiple frames, and generate a high-quality LUT.
                    </p>
                    
                    <div className="flex w-full max-w-md gap-2">
                      <input 
                        type="text" 
                        placeholder="Movie title..." 
                        value={movieQuery}
                        onChange={(e) => setMovieQuery(e.target.value)}
                        className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500"
                        onKeyDown={(e) => e.key === 'Enter' && handleMovieSearch()}
                      />
                      <button 
                        onClick={handleMovieSearch}
                        disabled={!movieQuery || processing}
                        className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {processing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              {error && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm text-center">
                  {error}
                </div>
              )}

            </div>
          </div>

          {/* Right Column: Result */}
          <div className="space-y-6">
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 h-full">
               <h3 className="text-lg font-semibold mb-6 flex items-center gap-2 text-slate-300">
                  <ImageIcon className="w-5 h-5 text-cyan-400" />
                  Extracted Grade
                </h3>

              {result ? (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  <div className="aspect-video bg-black rounded-lg overflow-hidden relative group border border-slate-700 shadow-2xl">
                    <img 
                      src={result.frame_url} 
                      alt="Analyzed frame" 
                      className="w-full h-full object-contain" 
                    />
                  </div>

                  <a 
                    href={result.lut_url}
                    download
                    className="block w-full py-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-center font-semibold text-lg transition-colors flex items-center justify-center gap-2 shadow-lg shadow-cyan-900/20"
                  >
                    <Download className="w-5 h-5" />
                    Download .CUBE
                  </a>
                  
                  <div className="p-4 bg-slate-950 rounded-xl text-xs text-slate-500">
                    <p>Import this .cube file into Premiere Pro (Lumetri Color), DaVinci Resolve, or Final Cut Pro to apply the look.</p>
                  </div>
                </div>
              ) : (
                <div className="h-[300px] flex flex-col items-center justify-center p-8 text-slate-600 border-2 border-dashed border-slate-800/50 rounded-xl">
                  <div className="w-16 h-16 rounded-full bg-slate-900 flex items-center justify-center mb-4">
                     <Download className="w-8 h-8 opacity-20" />
                  </div>
                  <p className="text-center">Select a frame or search a movie to generate your LUT.</p>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}

export default App
