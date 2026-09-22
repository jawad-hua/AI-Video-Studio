import type { GenerateRequest, StatusResponse, VideoInfo } from "@/types";
import type { HealthInfo, IdeasResponse, ProjectItem } from "@/types/projects";

// Sirf backend URL frontend mein hai. API keys kabhi frontend mein nahi aati.
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const absUrl = (path: string) => `${API_BASE}${path}`;

// status 0 = server tak pahunch hi nahi paye (backend band, network down)
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(absUrl(path), init);
  } catch {
    throw new ApiError("Cannot reach the server. Make sure the backend is running.", 0);
  }
  if (!res.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = "Please check your input and try again.";
    } catch {
      /* JSON nahi tha, generic message chalega */
    }
    throw new ApiError(message, res.status);
  }
  if (res.status === 204) return undefined as T; // DELETE: body nahi hoti
  return res.json() as Promise<T>;
}

export const createJob = (req: GenerateRequest) =>
  call<{ job_id: string }>("/api/video/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

export const getStatus = (jobId: string) => call<StatusResponse>(`/api/video/status/${jobId}`);

export const getVideo = (jobId: string) => call<VideoInfo>(`/api/video/${jobId}`);

export const getProjects = () => call<ProjectItem[]>("/api/projects");

export const deleteProject = (jobId: string) => call<void>(`/api/projects/${jobId}`, { method: "DELETE" });

export const getHealth = () => call<HealthInfo>("/api/health");

export const getIdeas = (niche: string, language: "en" | "ur" = "en") =>
  call<IdeasResponse>("/api/ideas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ niche: niche.trim() || null, language }),
  });
