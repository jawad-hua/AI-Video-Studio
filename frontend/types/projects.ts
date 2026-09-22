import type { JobStatus, VideoStyle } from "@/types";

// GET /api/projects
export interface ProjectItem {
  job_id: string;
  status: JobStatus;
  title: string;
  topic: string;
  style: VideoStyle;
  duration: number | null;
  elapsed_seconds: number | null;
  created_at: string;
  error: string | null;
  thumbnail_url: string | null;
  video_url: string | null;
  download_url: string | null;
}

// GET /api/health
export interface HealthInfo {
  status: string;
  ffmpeg: { found: boolean; version: string | null };
  config: {
    groq_api_key_set: boolean;
    pexels_api_key_set: boolean;
    groq_model: string;
    tts_provider: string;
    render_size: string;
  };
  warnings: string[];
}

// POST /api/ideas
export interface IdeasResponse {
  ideas: string[];
}
