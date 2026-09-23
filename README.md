---
title: AI Video Studio API
emoji: 🎬
colorFrom: blue
colorTo: purple
sdk: gradio
---

# 🎬 AI Video Studio

### AI-Powered Short-Form Video Generation Platform

AI Video Studio is a full-stack AI-powered video generation platform that transforms a simple idea into a complete professional short-form video.

The platform automatically handles **idea generation, script writing, scene planning, stock media selection, AI voiceovers, subtitles, transitions, effects, audio processing, and final video rendering**.

It is designed specifically for creating vertical content for **TikTok and Facebook Reels**, with videos up to **60 seconds** long.

---

## 🚀 Live Demo

### 🌐 Web Application

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open%20AI%20Video%20Studio-brightgreen?style=for-the-badge)](https://ai-video-studio-sigma-murex.vercel.app/)

**Live App:**  
https://ai-video-studio-sigma-murex.vercel.app/

### ⚙️ Backend API

[![Backend](https://img.shields.io/badge/Backend-Hugging%20Face-yellow?style=for-the-badge)](https://jawad-hua-ai-video-studio-api.hf.space)

**API:**  
https://jawad-hua-ai-video-studio-api.hf.space

### ❤️ API Health Check

https://jawad-hua-ai-video-studio-api.hf.space/api/health

---

## 📌 Project Overview

Creating high-quality short-form videos usually requires several different tools.

A creator may need one tool for:

- Generating ideas
- Writing scripts
- Finding stock footage
- Recording voiceovers
- Creating subtitles
- Adding transitions
- Editing scenes
- Mixing audio
- Rendering the final video

AI Video Studio combines these tasks into **one automated workflow**.

The user provides an idea or generates one with AI, selects the preferred video settings, and the system automatically builds the final video.

---

## 🔄 How It Works

```text
User Idea
    ↓
AI Idea Generation
    ↓
AI Script Generation
    ↓
Scene Planning
    ↓
Stock Media Search
    ↓
Media Download
    ↓
AI Voiceover
    ↓
Subtitle Generation
    ↓
Visual Effects
    ↓
Scene Transitions
    ↓
Audio Processing
    ↓
FFmpeg Rendering
    ↓
Final Vertical MP4 Video
```

---

# ✨ Main Features

## 💡 AI Idea Generator

Users can automatically generate video ideas based on a niche or topic.

Example niches include:

- Artificial Intelligence
- Technology
- Education
- Programming
- Productivity
- Motivation
- Business
- Social Media
- Custom topics

Instead of manually thinking about video ideas, the system can suggest content automatically.

---

## 🧠 AI Script Generation

AI Video Studio uses the **Groq API** to generate structured short-form video scripts.

The AI automatically creates:

- Video title
- Hook
- Narration
- Scene structure
- Scene descriptions
- Visual requirements
- Short-form optimized content

The generated script is divided into multiple scenes for automated video production.

---

## 🎞️ Intelligent Scene Planning

The script is automatically converted into individual video scenes.

Each scene contains information such as:

- Narration
- Scene duration
- Visual keywords
- Media requirements
- Subtitle content

This allows the system to automatically construct the complete video timeline.

---

## 📷 Automatic Stock Media Integration

AI Video Studio integrates with the **Pexels API** to automatically search for relevant:

- Stock videos
- Background footage
- Images

Media is selected based on the content of each generated scene.

The system also includes fallback handling when suitable stock footage is unavailable or a downloaded media file cannot be used.

---

## 🎙️ AI Voiceover Generation

Voiceovers are automatically generated using **Microsoft Edge TTS**.

The generated script is converted into natural speech without requiring manual voice recording.

This makes the platform useful for:

- Faceless videos
- Educational content
- AI content
- Technology videos
- Social media automation

---

## 💬 Automatic Subtitles

Subtitles are generated automatically from the narration.

The subtitle system is designed for vertical short-form videos and keeps text synchronized with the generated voiceover.

This helps improve:

- Accessibility
- Viewer retention
- Mobile viewing
- Social media engagement

---

## 🎬 Professional Video Rendering

The final video is produced using **FFmpeg**.

The rendering engine combines:

- Video clips
- Images
- AI voiceovers
- Background music
- Subtitles
- Scene timing
- Visual effects
- Transitions
- Zoom effects

into one final MP4 video.

---

## 🔀 Scene Transitions

AI Video Studio supports multiple transitions and visual effects.

Examples include:

- Crossfade
- Slide
- Zoom
- Ken Burns effect
- Scene-to-scene transitions

These effects help generated videos look more polished than simple slideshow-style AI videos.

---

## 🎵 Audio Processing

The platform supports audio processing and mixing for generated videos.

The rendering pipeline can combine:

```text
Voiceover
    +
Background Music
    ↓
Final Audio Track
```

The audio track is then synchronized with the final video.

---

## 📱 Vertical Video Optimization

AI Video Studio is designed primarily for short-form social media.

Default production format:

```text
Resolution: 720 × 1280
Aspect Ratio: 9:16
Maximum Duration: 60 seconds
Video Format: MP4
```

Optimized for:

- TikTok
- Facebook Reels
- Vertical social media videos
- Faceless content
- Educational short videos

---

## 🕒 Video Duration Options

The platform supports short-form video generation including:

```text
30 seconds
45 seconds
60 seconds
```

The maximum target video duration is **1 minute**.

---

## 📚 Video History

Generated videos can be tracked through the History section.

Users can review previous video-generation jobs and access previously rendered videos while they remain available on the backend.

---

## ⚙️ Settings Management

The frontend includes configurable video-generation settings.

Users can control different parts of the video generation workflow directly through the interface.

---

# 🛠️ Technology Stack

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

## Backend

- Python
- FastAPI
- Uvicorn

## Artificial Intelligence

- Groq API
- GPT-OSS model

Current model:

```text
openai/gpt-oss-120b
```

## Stock Media

- Pexels API

## Text-to-Speech

- Microsoft Edge TTS

## Video Processing

- FFmpeg
- FFprobe

## Deployment

### Frontend

- Vercel

### Backend

- Hugging Face Spaces

## Version Control

- Git
- GitHub

---

# 🏗️ System Architecture

```text
┌───────────────────────────────────┐
│                                   │
│        Next.js Frontend           │
│                                   │
│              Vercel               │
│                                   │
└─────────────────┬─────────────────┘
                  │
                  │ REST API
                  │
                  ▼
┌───────────────────────────────────┐
│                                   │
│        FastAPI Backend            │
│                                   │
│       Hugging Face Spaces         │
│                                   │
└─────────────────┬─────────────────┘
                  │
          ┌───────┼────────┐
          │       │        │
          ▼       ▼        ▼
       Groq     Pexels   Edge TTS
          │       │        │
          └───────┼────────┘
                  │
                  ▼
               FFmpeg
                  │
                  ▼
          Final MP4 Video
```

---

# 🧠 AI Workflow

The AI pipeline follows several stages.

### 1. Idea Generation

The system generates short-form content ideas according to the user's selected niche.

```text
Niche
  ↓
Groq AI
  ↓
Video Ideas
```

### 2. Script Generation

The selected idea is converted into a structured script.

```text
Idea
  ↓
AI Script
  ↓
Scenes
```

### 3. Media Retrieval

Visual keywords from each scene are used to search Pexels.

```text
Scene
  ↓
Keywords
  ↓
Pexels API
  ↓
Stock Media
```

### 4. Voice Generation

Scene narration is converted into speech.

```text
Narration
  ↓
Edge TTS
  ↓
Voiceover
```

### 5. Subtitle Generation

Subtitle timing is generated according to the narration.

### 6. Video Rendering

FFmpeg combines all assets.

```text
Media
 +
Voice
 +
Subtitles
 +
Music
 +
Transitions
    ↓
 FFmpeg
    ↓
Final Video
```

---

# 📂 Project Structure

```text
AI-Video-Studio/
│
├── backend/
│   │
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── main.py
│   │   └── config.py
│   │
│   ├── assets/
│   │   └── fonts/
│   │
│   ├── generated/
│   │
│   └── requirements.txt
│
├── frontend/
│   │
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
│
├── app.py
├── Dockerfile
├── requirements.txt
├── PROJECT_STATE.md
└── README.md
```

---

# 🔐 Environment Variables

## Backend

The backend requires the following environment variables:

```env
GROQ_API_KEY=your_groq_api_key
PEXELS_API_KEY=your_pexels_api_key
GROQ_MODEL=openai/gpt-oss-120b
FRONTEND_URL=https://your-frontend-domain.vercel.app
```

Never commit actual API keys to GitHub.

Production secrets should be configured through the hosting platform.

---

## Frontend

Create the following environment variable:

```env
NEXT_PUBLIC_API_URL=https://your-backend-url.hf.space
```

Current production backend:

```env
NEXT_PUBLIC_API_URL=https://jawad-hua-ai-video-studio-api.hf.space
```

---

# 💻 Local Installation

## 1. Clone Repository

```bash
git clone https://github.com/jawad-hua/AI-Video-Studio.git
```

Enter the project:

```bash
cd AI-Video-Studio
```

---

# ⚙️ Backend Setup

Move into the backend:

```bash
cd backend
```

Create a Python virtual environment:

```bash
python -m venv venv
```

### Activate on Windows

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file and configure:

```env
GROQ_API_KEY=your_groq_api_key
PEXELS_API_KEY=your_pexels_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

Backend should start at:

```text
http://localhost:8000
```

---

# 🖥️ Frontend Setup

Open another terminal.

Move into:

```bash
cd frontend
```

Install Node dependencies:

```bash
npm install
```

Create:

```text
.env.local
```

Add:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start development server:

```bash
npm run dev
```

Frontend should run at:

```text
http://localhost:3000
```

---

# ❤️ Backend Health Check

AI Video Studio includes an API health endpoint.

```http
GET /api/health
```

Production endpoint:

```text
https://jawad-hua-ai-video-studio-api.hf.space/api/health
```

The endpoint checks:

- Backend status
- FFmpeg installation
- Groq API configuration
- Pexels API configuration
- Active Groq model
- TTS provider
- Render resolution

Example response:

```json
{
  "status": "ok",
  "app": "AI Video Studio API",
  "ffmpeg": {
    "found": true
  },
  "config": {
    "groq_api_key_set": true,
    "pexels_api_key_set": true,
    "groq_model": "openai/gpt-oss-120b",
    "tts_provider": "edge",
    "render_size": "720x1280"
  },
  "warnings": []
}
```

---

# 🌐 Production Deployment

AI Video Studio uses a separated frontend and backend deployment architecture.

```text
GitHub
   │
   ├───────────────► Vercel
   │                    │
   │                    └── Next.js Frontend
   │
   │
   └───────────────► Hugging Face Spaces
                        │
                        └── FastAPI Backend
                                │
                                ├── Groq
                                ├── Pexels
                                ├── Edge TTS
                                └── FFmpeg
```

---

# ✅ Current Capabilities

AI Video Studio currently supports:

- AI-powered video idea generation
- Niche-based idea generation
- Automated script writing
- Scene-by-scene planning
- Stock media discovery
- Pexels integration
- Automated media downloading
- AI voiceover generation
- Automatic subtitles
- Subtitle synchronization
- Background music
- Audio mixing
- Ken Burns effects
- Scene transitions
- Zoom effects
- FFmpeg-based rendering
- Vertical 9:16 videos
- Videos up to 60 seconds
- Video job processing
- Generation history
- Web-based dashboard
- Production frontend deployment
- Production backend deployment

---

# 🎯 Use Cases

AI Video Studio can be useful for:

### Social Media Creators

Create short-form vertical content quickly.

### Faceless Content

Generate videos without recording yourself.

### Educational Content

Turn educational ideas into narrated short videos.

### AI & Technology Content

Create videos about:

- Artificial Intelligence
- Machine Learning
- Automation
- Programming
- Emerging technology

### Marketing

Create short promotional or informational videos.

### Content Automation

Automate several repetitive parts of the content creation workflow.

---

# 🚀 Future Improvements

Potential future improvements include:

- Advanced audio ducking
- More AI voice options
- Multiple subtitle themes
- Additional video transition styles
- AI thumbnail generation
- Improved media ranking
- Multiple stock media providers
- Persistent cloud video storage
- Improved concurrent job handling
- User authentication
- User accounts
- Cloud database integration
- Automatic TikTok publishing
- Automatic Facebook publishing
- Social media scheduling
- Advanced video templates
- Branding presets
- AI-generated background images
- Improved rendering performance

---

# ⚠️ Deployment Notes

The backend currently runs on Hugging Face Spaces.

Generated files stored locally by the backend may not be permanently retained if the Space restarts or its temporary filesystem is reset.

For a larger production deployment, persistent object storage such as S3-compatible storage or Cloudinary can be integrated.

---

# 🎓 Project Purpose

AI Video Studio was developed as a practical AI engineering project to explore how multiple modern technologies can work together in a real application.

The project combines:

- Generative AI
- REST APIs
- Backend development
- Frontend development
- Text-to-speech
- Media APIs
- Video processing
- FFmpeg
- Cloud deployment
- Automation

The goal is to demonstrate a complete end-to-end AI-powered content creation workflow rather than only a standalone AI model.

---

# 👨‍💻 Author

## Muhammad Jawad

AI • Machine Learning • Automation • Python

GitHub:

https://github.com/jawad-hua

---

# 🔗 Important Links

### Live Application

https://ai-video-studio-sigma-murex.vercel.app/

### GitHub Repository

https://github.com/jawad-hua/AI-Video-Studio

### Backend API

https://jawad-hua-ai-video-studio-api.hf.space

### Backend Health Check

https://jawad-hua-ai-video-studio-api.hf.space/api/health

---

# ⭐ Support

If you find this project useful or interesting, consider giving the repository a **star ⭐**.

It helps support the project and its future development.

---

## Built with

**Python • FastAPI • Next.js • TypeScript • Groq • Pexels • Edge TTS • FFmpeg • Hugging Face • Vercel**