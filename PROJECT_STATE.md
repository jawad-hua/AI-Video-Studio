# PROJECT_STATE

## AI Video Studio

AI Video Studio is a full-stack AI-powered short-form video generation platform for creating professional vertical videos for TikTok and Facebook.

The application can generate ideas, scripts, stock media, AI voiceovers, subtitles, transitions, effects, and final rendered videos automatically.

---

## Current Status

**Status: Production deployment working**

The complete application has been successfully deployed and tested.

### Production

Frontend:
https://ai-video-studio-sigma-murex.vercel.app/

Backend:
https://jawad-hua-ai-video-studio-api.hf.space

Backend health:
https://jawad-hua-ai-video-studio-api.hf.space/api/health

### Verified Production Tests

The following have been tested successfully:

- Frontend loads successfully on Vercel
- Frontend communicates with Hugging Face backend
- Backend health endpoint works
- Groq API configuration works
- Pexels API configuration works
- FFmpeg is available in production
- AI Idea Generator works
- Script generation works
- Stock media fetching works
- Edge TTS voice generation works
- Subtitle generation works
- FFmpeg rendering works
- 30-second video generation works
- 60-second video generation works
- Vertical 9:16 video generation works
- Full end-to-end production workflow works

---

# Completed Development Phases

## Phase 1 — Architecture and Project Setup

Completed:

- Backend architecture
- Frontend architecture
- Project folder structure
- Environment configuration
- API design
- Video-generation pipeline design

---

## Phase 2 — Frontend Interface

Completed:

- Next.js frontend
- TypeScript
- Tailwind CSS
- Modern dashboard-style interface
- Create Video page
- Projects page
- Templates page
- Settings page
- Responsive layout
- Sidebar navigation

---

## Phase 3 — FastAPI Backend

Completed:

- FastAPI application
- Uvicorn server
- API routers
- Error handling
- Startup lifecycle
- Generated-file directories
- Health endpoint

Health API:

```text
GET /api/health
```

---

## Phase 4 — AI Script Generation

Completed:

```text
POST /api/script/generate
```

AI provider:

```text
Groq
```

Production model:

```text
openai/gpt-oss-120b
```

The model is configured through:

```text
GROQ_MODEL
```

instead of being hardcoded for production.

---

## Phase 5 — Pexels Media Integration

Completed:

```text
POST /api/media/fetch
```

Media priority:

```text
Vertical stock video
        ↓
Stock photo
        ↓
Local fallback
```

Pexels API is used to retrieve media related to generated scenes.

---

## Phase 6 — AI Voice Generation

Completed:

```text
POST /api/voice/generate
```

TTS provider:

```text
Microsoft Edge TTS
```

Features:

- Automatic narration
- Multiple voices
- English support
- Urdu support
- Scene-specific audio
- Word timing support

---

## Phase 7 — Subtitle Engine

Completed:

```text
POST /api/subtitles/generate
```

Subtitle format:

```text
ASS
```

Features:

- Automatic subtitle generation
- Safe-zone positioning
- Styled subtitles
- Karaoke-style highlighting
- Word-level timing
- English support
- Urdu subtitle support

Bundled fonts include:

- Poppins Bold
- Noto Naskh Arabic Bold

---

## Phase 8 — FFmpeg Video Rendering

Completed:

```text
POST /api/render/generate
```

Rendering engine:

```text
FFmpeg
```

Features:

- Scene rendering
- Video clips
- Image clips
- Voiceover
- Background music
- ASS subtitles
- Transitions
- Colour grading
- Zoom effects
- Ken Burns effects
- Audio processing
- Final MP4 export

---

## Phase 9 — Full Video Generation Pipeline

Completed:

```text
POST /api/video/generate
```

Main generation flow:

```text
Idea
  ↓
Script
  ↓
Scene Planning
  ↓
Media Fetch
  ↓
Voice Generation
  ↓
Subtitle Generation
  ↓
Video Rendering
  ↓
Final MP4
```

---

## Phase 9B — Application Pages

Completed:

- Create Video
- Dashboard
- Projects
- Templates
- Settings

Navigation is integrated into the application shell.

---

## Phase 10 — Job System and Production Reliability

Completed:

- Background video worker
- Job queue
- Job status tracking
- Progress tracking
- Job history
- Error handling
- Cleanup
- Old-project pruning
- Windows file-lock handling
- Retry handling
- FFmpeg safety improvements
- Friendly frontend errors

---

# Upgrade 1 — Dashboard and Workflow Improvements

Completed:

- Dashboard
- AI Idea Generator
- Quick Create
- Recent Videos
- System Status
- Post Kit
- AI captions
- AI hashtags
- Watermark support
- Estimated generation time
- Job timings
- Improved render speed

---

# Upgrade 2 — Video Effects and Professional Rendering

Completed:

## Transitions

Transition selection varies according to video style.

Examples:

- Fade
- Smooth slide
- Zoom
- Circle open
- Radial
- Slice
- Fade white
- Fade black
- Dissolve

Transitions avoid unnecessary repeated patterns where possible.

---

## Visual Effects

Completed:

- Style-specific colour grading
- Fade-in
- Fade-out
- Slow stock-video movement
- Ken Burns effect for images
- Optional vignette
- Zoom and crop effects

---

## Sound Effects

Completed:

- Transition whoosh effects
- Optional sound effects
- Background music integration
- Voice/music mixing

---

## Rendering Fallback Strategy

Rendering uses multiple fallback levels:

```text
Full effects
    ↓
Simplified transitions + music
    ↓
Hard cuts
```

This improves generation reliability when an FFmpeg effect fails.

---

# Karaoke Subtitle System

Completed:

- Word-by-word highlighting
- Base subtitle layer
- Active-word highlighting
- Word timing support
- Voice timing synchronization

Styles may vary according to selected video style.

---

# Urdu Subtitle Support

Completed improvements:

- Noto Naskh Arabic font bundled
- RTL handling
- Urdu positioning fixes
- Urdu/English mixed-line handling
- Word-order handling
- Subtitle rendering verification logic

Urdu subtitles use additional handling because FFmpeg/libass behaviour can vary with RTL text.

---

# Idea Generator

Completed:

```text
POST /api/ideas
```

Users can enter a niche such as:

```text
AI
Technology
Programming
Education
Motivation
Business
Productivity
```

The system returns AI-generated short-form video ideas.

Production test:

```text
Working
```

---

# Video Job System

A generated video is represented by a unique job ID.

Job data is stored under:

```text
backend/generated/jobs/
```

Job status flow:

```text
queued
   ↓
analyzing
   ↓
scripting
   ↓
fetching_media
   ↓
generating_voice
   ↓
creating_subtitles
   ↓
rendering
   ↓
completed
```

Possible failure state:

```text
failed
```

The backend processes video jobs through a background worker.

---

# Main Video APIs

## Start Generation

```text
POST /api/video/generate
```

Returns:

```json
{
  "job_id": "..."
}
```

---

## Job Status

```text
GET /api/video/status/{job_id}
```

Returns information such as:

- Status
- Progress
- Current step
- Error
- Timing information

---

## Video Information

```text
GET /api/video/{job_id}
```

Contains information such as:

- Video title
- Scenes
- Video URL
- Download URL

---

## Video File

```text
GET /api/video/{job_id}/file
```

---

## Download Video

```text
GET /api/video/{job_id}/download
```

---

## Scene Thumbnail

```text
GET /api/video/{job_id}/thumb/{scene_number}
```

---

# Project APIs

```text
GET /api/projects
```

Returns generated projects.

```text
DELETE /api/projects/{job_id}
```

Deletes eligible completed or failed projects and their generated files.

---

# Production Configuration

## Backend

Framework:

```text
FastAPI
```

Hosting:

```text
Hugging Face Spaces
```

Space URL:

```text
https://jawad-hua-ai-video-studio-api.hf.space
```

Application port:

```text
7860
```

---

## Frontend

Framework:

```text
Next.js
```

Hosting:

```text
Vercel
```

Production URL:

```text
https://ai-video-studio-sigma-murex.vercel.app/
```

Frontend backend configuration:

```text
NEXT_PUBLIC_API_URL=https://jawad-hua-ai-video-studio-api.hf.space
```

---

# Backend Environment Variables

Required:

```env
GROQ_API_KEY=<secret>
PEXELS_API_KEY=<secret>
GROQ_MODEL=openai/gpt-oss-120b
FRONTEND_URL=https://ai-video-studio-sigma-murex.vercel.app
```

API keys must never be committed to Git.

Production secrets are stored in Hugging Face Spaces settings.

---

# CORS

Production CORS supports:

```text
http://localhost:3000
http://127.0.0.1:3000
```

and the deployed frontend URL through:

```text
FRONTEND_URL
```

This allows both local development and the Vercel frontend to communicate with the backend.

---

# Hugging Face Deployment

The backend is deployed using a Hugging Face Gradio Space while serving the FastAPI application through Uvicorn.

Root deployment files include:

```text
app.py
requirements.txt
README.md
```

The root application starts the backend on:

```text
0.0.0.0:7860
```

Hugging Face provides FFmpeg in the runtime environment.

Production health check confirms FFmpeg is available.

---

# Vercel Deployment

The frontend is deployed from:

```text
frontend/
```

Vercel framework:

```text
Next.js
```

Environment variable:

```text
NEXT_PUBLIC_API_URL
```

points to the Hugging Face backend.

---

# Production Health Check

Endpoint:

```text
https://jawad-hua-ai-video-studio-api.hf.space/api/health
```

Verified production state:

```text
status: ok

FFmpeg: available

Groq API key: configured

Pexels API key: configured

Groq model:
openai/gpt-oss-120b

TTS:
edge

Render:
720x1280
```

---

# Video Output

Default resolution:

```text
720 × 1280
```

Aspect ratio:

```text
9:16
```

Maximum target duration:

```text
60 seconds
```

Format:

```text
MP4
```

Target platforms:

- TikTok
- Facebook Reels
- Short-form social media

---

# Performance

The rendering pipeline includes performance optimizations such as:

- Parallel scene TTS
- Parallel media and voice processing
- FFmpeg optimized presets
- Reduced intermediate rendering overhead
- Configurable speed mode
- Job timing tracking

Available speed strategies include:

```text
fast
balanced
```

Default production goal:

```text
fast
```

---

# Project Structure

```text
AI-Video-Studio/
│
├── backend/
│   │
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── config.py
│   │   └── main.py
│   │
│   ├── assets/
│   │   ├── fonts/
│   │   └── music/
│   │
│   ├── generated/
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   ├── types/
│   └── package.json
│
├── app.py
├── Dockerfile
├── requirements.txt
├── README.md
└── PROJECT_STATE.md
```

---

# Frontend API Configuration

Frontend API client:

```text
frontend/lib/api.ts
```

API base:

```text
NEXT_PUBLIC_API_URL
```

Local fallback:

```text
http://localhost:8000
```

---

# Local Development

## Backend

```bash
cd backend
```

Activate virtual environment:

```bash
venv\Scripts\activate
```

Run:

```bash
uvicorn app.main:app --reload --port 8000
```

Backend:

```text
http://localhost:8000
```

---

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:3000
```

Local frontend environment:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

# Offline Tests

Backend tests include checks for:

```text
script logic
Pexels logic
voice logic
subtitle logic
render logic
job logic
project logic
```

Example:

```bash
python -m tests.check_script_logic
```

```bash
python -m tests.check_pexels_logic
```

```bash
python -m tests.check_voice_logic
```

```bash
python -m tests.check_subtitle_logic
```

```bash
python -m tests.check_render_logic
```

```bash
python -m tests.check_jobs_logic
```

```bash
python -m tests.check_projects_logic
```

---

# Current Production Test Result

## Idea Generation

```text
PASS
```

## Backend API

```text
PASS
```

## Groq

```text
PASS
```

## Pexels

```text
PASS
```

## Edge TTS

```text
PASS
```

## FFmpeg

```text
PASS
```

## Frontend → Backend Connection

```text
PASS
```

## 30 Second Video

```text
PASS
```

## 60 Second Video

```text
PASS
```

## Production Deployment

```text
PASS
```

---

# Current Limitations

## Temporary Local Storage

Generated files currently use the backend filesystem.

On Hugging Face Spaces, local generated files should not be considered permanent cloud storage.

A future production upgrade can move generated videos to:

- Cloudinary
- Amazon S3
- Cloudflare R2
- Supabase Storage
- another S3-compatible service

---

## Job Concurrency

The current worker is intentionally conservative.

The backend processes video generation through a controlled queue to avoid excessive resource use.

Future versions can improve concurrent job processing.

---

## Authentication

The current application does not provide a complete production user-account/authentication system.

For a public high-traffic deployment, authentication and rate limiting should be added.

---

# Future Improvements

Possible next upgrades:

- Persistent cloud video storage
- User authentication
- Rate limiting
- Multiple users
- Improved concurrent rendering
- Advanced audio ducking
- More AI voices
- More subtitle themes
- Additional transitions
- More video templates
- AI thumbnail generation
- Multiple media providers
- User branding presets
- Automatic Facebook publishing
- Automatic TikTok publishing
- Social media scheduling
- Analytics
- Cloud database integration
- Production monitoring

---

# Important Technical Decisions

## Backend

```text
FastAPI + Python
```

## Frontend

```text
Next.js + TypeScript + Tailwind CSS
```

## AI

```text
Groq
```

## Production AI Model

```text
openai/gpt-oss-120b
```

## Media

```text
Pexels
```

## Voice

```text
Edge TTS
```

## Video Engine

```text
FFmpeg
```

## Frontend Hosting

```text
Vercel
```

## Backend Hosting

```text
Hugging Face Spaces
```

---

# Security Decisions

- API keys stay on the backend
- API keys are not exposed to the Next.js frontend
- Production secrets are configured through hosting environment variables
- `.env` is not intended for Git commits
- Frontend only receives the public backend URL

---

# Final Project State

The core AI Video Studio application is now complete and deployed.

The full production workflow has been tested successfully:

```text
User
  ↓
Vercel Frontend
  ↓
Hugging Face FastAPI Backend
  ↓
Groq
  ↓
Pexels
  ↓
Edge TTS
  ↓
Subtitles
  ↓
FFmpeg
  ↓
Final Vertical Video
```

Current project state:

```text
Development: COMPLETE
Core Features: COMPLETE
Frontend Deployment: COMPLETE
Backend Deployment: COMPLETE
API Integration: WORKING
30-second Generation: WORKING
60-second Generation: WORKING
Production Test: PASSED
```

---

# Next Development Stage

The project has moved from core development into:

```text
Production hardening
+
Portfolio presentation
+
Optional advanced features
```

The highest-value next improvements are:

```text
1. Persistent cloud video storage
2. Authentication and rate limiting
3. Better concurrent job handling
4. Deployment monitoring
5. Social media publishing automation
```

---

Last production verification:

```text
September 2026
```

