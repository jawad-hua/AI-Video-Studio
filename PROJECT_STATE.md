# PROJECT_STATE

## Completed phases
- Phase 1: Architecture + setup
- Phase 2: Frontend UI with mock data
- Phase 3: FastAPI backend + /api/health
- Phase 4: Groq script (POST /api/script/generate), model openai/gpt-oss-120b
- Phase 5: Pexels media (POST /api/media/fetch)
- Phase 6: edge-tts voice (POST /api/voice/generate)
- Phase 7: ASS subtitles (POST /api/subtitles/generate)
- Phase 8: FFmpeg render (POST /api/render/generate)
- Phase 9: Frontend connected to real backend + basic job system (POST /api/video/generate)
- Phase 9b (user ki request): sidebar clickable + Projects / Templates / Settings pages
- Phase 10: real progress, preflight, cleanup + prune, safer ffmpeg
- Phase 10b: Windows file-lock fix (job_service RLock + retry)
- Upgrade 1 (user ki request): Dashboard + speed (2.6x) + Post kit (caption/hashtags) + Ideas + Watermark + ETA
- Upgrade 2 (user ki request): pro transitions + colour grade + whoosh sounds + karaoke subtitles

## Current phase
Upgrade done. Phase 11 (final polish + real-world testing) abhi baaki hai. Waiting for NEXT

## API (frontend yehi use karta hai)
- POST /api/video/generate  -> {job_id}   (body: topic, duration, aspect_ratio, style, voice, resolution, background_music)
- GET  /api/video/status/{job_id} -> {status, progress, current_step, error}
- GET  /api/video/{job_id} -> VideoInfo (title, scenes, video_url, download_url)  [409 agar ready nahi]
- GET  /api/video/{job_id}/file | /download | /thumb/{scene_number}
- Status flow: queued > analyzing > scripting > fetching_media > generating_voice > creating_subtitles > rendering > completed | failed
- Progress abhi stage-based (5,10,25,50,68,75,100). Rendering (75->100) lambi hoti hai: Phase 10 mein ffmpeg se real progress.

## Pages (frontend)
- / Create Video | /projects (list, watch, download, delete) | /templates (form prefill via sessionStorage 'template') | /settings (health check: FFmpeg, keys set/missing, model)
- Dashboard abhi disabled ("Soon")
- Layout: components/AppShell.tsx (sidebar + background) app/layout.tsx mein
- API: GET /api/projects, DELETE /api/projects/{job_id} (sirf completed/failed delete hote hain, saari files hat jati hain)

## Upgrade features (Sept 2026)
- Speed: TTS 3 scenes parallel; media + voice ek saath; intermediates ultrafast; final preset speed=fast (superfast, crf+2) ya balanced (veryfast).
  Benchmark (1-core container, 35s video): purana 79s -> balanced 47s -> fast 30s. Default "fast". Request field: speed.
- Dashboard (/dashboard): stats, quick create, AI ideas (POST /api/ideas), recent videos, system status.
- Post kit: script ke saath AI caption + hashtags (VideoPlan.caption/hashtags) -> result page par Copy buttons.
- Watermark: Settings > Branding (localStorage 'watermark') -> request.watermark -> ASS 'Brand' style, top-left.
- ETA: job.started_at/elapsed_seconds/timings; status mein elapsed_seconds + typical_seconds (last 5 jobs ka average).
- Job timings (script, media_voice, subtitles, render, cleanup, total) job JSON aur app.log mein.

## Upgrade 2: effects + subtitles
- Transitions: style ke hisaab se pool (app/services/effects.py), seed=job_id, lagatar repeat nahi. modern-tech: smoothleft, slideup, circleopen, zoomin, radial, hlslice, fadewhite...; cinematic: fadeblack, dissolve, fadewhite, smoothup...
  Sab 14 xfade names ffmpeg 6.1 par verify. Plan ki transition (fade/slide/zoom) ab use nahi hoti.
- Look: colour grade per style (eq / colorbalance), fade-in 0.35s + fade-out 0.5s, stock videos par slow pan (10% zoom + crop), images par Ken Burns.
  Vignette sirf speed=balanced mein (CPU-bhaari: ~8s extra).
- Sound: transition par whoosh (FFmpeg pink noise se banti hai, koi download nahi), volume 0.30; request field sound_effects; Advanced settings mein toggle.
- Fallback: (1) poore effects (2) sirf fade + music (3) seedhe cuts bina music. RenderResult.transition_names batata hai kya lagi.
- Subtitles: word-by-word highlight (karaoke). Base line (layer 0, pop animation) + har lafz ka overlay event (layer 1, sirf us lafz ka fill rang badalta hai: \1a alpha trick).
  Highlight colours: modern-tech gold, cinematic amber, documentary sky blue, minimal: koi highlight nahi.
- Word timing: edge-tts boundary="WordBoundary" se asli timings (voice.json items[].words); validate (ginti, tarteeb, unit sanity), na mile to characters ke hisaab se andaza. Speed-up par scale hote hain.
  NOTE: real Microsoft edge-tts par WordBoundary abhi live test nahi hua (offline fake se test).
- Speed (35s test video, 1 core): fast 26.7s (ultrafast final, no vignette), balanced 61.9s. Fast mein file bari hoti hai (ultrafast) lekin quality same.

## Urdu subtitle fix
- Masla: Urdu subtitles ulte/galat dikhte the. Wajah: (1) overlay-layer highlight ka layout base se hil jata tha, (2) libass Urdu+English line ko LTR base mein rakhta tha, (3) Segoe UI par bharosa.
- Fix: highlight ab har lafz ka apna event (overlay nahi); RTL lines par RLE...PDF (U+202B/U+202C); font bundled: Noto Naskh Arabic Bold (assets/fonts, OFL), size x1.2.
- Highlight sirf pure-Urdu chunks mein. Urdu+English (Latin) chunk mein highlight band (libass mein lafz ulte-seedhe hote the).
- libass ke rang-runs kuch builds mein LTR lagte hain: subtitle_service._runs_are_ltr() asli ffmpeg se check karta hai aur zarurat par runs ka order khud ulta karta hai. Check na ho paye to Urdu mein highlight band.
- Test: python -m tests.check_subtitle_logic ("Urdu order check: OK" pixel se verify karta hai: pehla lafz dayen, aakhri bayen).

## Decisions
- Backend: FastAPI, Frontend: Next.js 15 + TS + Tailwind v4 + lucide-react
- Job system: generated/jobs/{job_id}.json (12 hex chars) + {job_id}_plan.json; ek background worker thread (pipeline_service), ek waqt mein ek job, max 3 pending (429).
  Server restart par adhoore jobs "failed" mark hote hain (mark_stale_jobs_failed).
- Frontend: lib/api.ts (API_BASE = NEXT_PUBLIC_API_URL ya http://localhost:8000), hooks/useVideoJob.ts (2 sec polling, 3 network failures par error), lib/config.ts (STEPS, VOICES, STYLES)
- Language: voice "ur-*" ho to script Urdu mein, warna English
- Groq via httpx, GROQ_MODEL=openai/gpt-oss-120b (reasoning_effort=low)
- Media: Pexels vertical video > photo > local placeholder PNG
- Voice: edge-tts; scene duration = audio + 0.4s; total <= 60
- Subtitles: ASS, Poppins Bold (assets/fonts), safe-zone margins
- Render: per-scene clips + xfade + narration + subtitles + optional music (assets/music); fallback to hard cuts; relative paths for ffmpeg filters (Windows)
- Errors: AppError(message, status) -> friendly message, details generated/app.log
- Backend run: cd backend; venv\Scripts\activate; uvicorn app.main:app --reload --port 8000
- Frontend run: cd frontend; npm install; npm run dev  (http://localhost:3000)
- Offline tests: python -m tests.check_script_logic | check_pexels_logic | check_voice_logic | check_subtitle_logic | check_render_logic | check_jobs_logic | check_projects_logic
- Windows: cmd use ho raha hai; tests/ mein __init__.py zaroori

## Known errors
- Real Pexels, real edge-tts, real render abhi user ke Windows par live test nahi hue
- Urdu subtitle look aur render speed (4GB RAM) real run par check karna hai
- Frontend obsolete files delete karni hain: frontend/hooks/useMockGeneration.ts, frontend/lib/mock.ts

## Next task
Phase 10: Progress tracking + error handling polish (real render progress from ffmpeg, cleanup of old job files, friendlier error cases, retry)
