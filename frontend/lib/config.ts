import type { JobStatus, StepDef, VideoStyle } from "@/types";

export const STEPS: StepDef[] = [
  { id: "analyze", activeLabel: "Analyzing topic", doneLabel: "Topic analyzed" },
  { id: "script", activeLabel: "Generating script", doneLabel: "Script generated" },
  { id: "scenes", activeLabel: "Creating scenes", doneLabel: "Scenes created" },
  { id: "media", activeLabel: "Collecting media", doneLabel: "Media collected" },
  { id: "voice", activeLabel: "Generating voice", doneLabel: "Voice generated" },
  { id: "subtitles", activeLabel: "Creating subtitles", doneLabel: "Subtitles created" },
  { id: "render", activeLabel: "Rendering video", doneLabel: "Video rendered" },
];

// Backend ka status -> upar wali STEPS list mein kaunsa step "active" hai
// (script aur scenes backend mein ek hi step hain, isliye scripting ke baad seedha media par jump)
const STEP_INDEX: Record<JobStatus, number> = {
  queued: 0,
  analyzing: 0,
  scripting: 1,
  fetching_media: 3,
  generating_voice: 4,
  creating_subtitles: 5,
  rendering: 6,
  completed: STEPS.length,
  failed: 0,
};

export function stepIndexFor(status: JobStatus | undefined): number {
  return status ? STEP_INDEX[status] : 0;
}

export const VOICES = [
  { id: "en-US-AndrewNeural", label: "Andrew (English, male)" },
  { id: "en-US-AriaNeural", label: "Aria (English, female)" },
  { id: "ur-PK-AsadNeural", label: "Asad (Urdu, male)" },
  { id: "ur-PK-UzmaNeural", label: "Uzma (Urdu, female)" },
];

export const STYLES: { id: VideoStyle; label: string; hint: string }[] = [
  { id: "cinematic", label: "Cinematic", hint: "Slow zooms, dramatic mood" },
  { id: "modern-tech", label: "Modern Tech", hint: "Clean, fast, punchy" },
  { id: "documentary", label: "Documentary", hint: "Calm, informative" },
  { id: "minimal", label: "Minimal", hint: "Simple and quiet" },
];

export const EXAMPLES = [
  "Explain Agentic AI in simple terms",
  "How Generative AI is changing software development",
  "5 habits of highly productive developers",
];
