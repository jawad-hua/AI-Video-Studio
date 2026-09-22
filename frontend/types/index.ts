export type VideoStyle = "cinematic" | "modern-tech" | "documentary" | "minimal";
export type Resolution = "720p" | "1080p";
export type StepState = "done" | "active" | "pending";

// POST /api/video/generate ki request (backend GenerateVideoRequest se same names)
export interface GenerateRequest {
  topic: string;
  duration: 30 | 45 | 60;
  aspect_ratio: "9:16";
  style: VideoStyle;
  voice: string;
  resolution: Resolution;
  background_music: boolean;
  speed: "fast" | "balanced";
  sound_effects: boolean;
  watermark: string | null;
}

export type JobStatus =
  | "queued"
  | "analyzing"
  | "scripting"
  | "fetching_media"
  | "generating_voice"
  | "creating_subtitles"
  | "rendering"
  | "completed"
  | "failed";

// GET /api/video/status/{job_id}
export interface StatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  current_step: string;
  error: string | null;
  elapsed_seconds: number;
  typical_seconds: number | null; // pichhli videos ka average time
}

export interface SceneInfo {
  number: number;
  start: number;
  duration: number;
  narration: string;
  subtitle: string;
  media_type: "video" | "image";
  media_source: "pexels" | "fallback";
  thumbnail_url: string; // relative path, absUrl() se poora URL banta hai
}

// GET /api/video/{job_id}
export interface VideoInfo {
  job_id: string;
  title: string;
  topic: string;
  style: VideoStyle;
  duration: number;
  width: number;
  height: number;
  size_mb: number;
  caption: string;
  hashtags: string[];
  elapsed_seconds: number | null;
  video_url: string;
  download_url: string;
  scenes: SceneInfo[];
}

export interface StepDef {
  id: string;
  activeLabel: string;
  doneLabel: string;
}
