import type { VideoStyle } from "@/types";

export interface Template {
  id: string;
  name: string;
  description: string;
  topic: string;
  style: VideoStyle;
  duration: 30 | 45 | 60;
}

export const TEMPLATES: Template[] = [
  { id: "tech", name: "Tech Explainer", description: "Complex tech idea in simple words", topic: "Explain Agentic AI in simple terms", style: "modern-tech", duration: 60 },
  { id: "facts", name: "Quick Facts", description: "Short, surprising facts", topic: "5 surprising facts about the human brain", style: "minimal", duration: 30 },
  { id: "motivation", name: "Motivation", description: "Emotional, cinematic pep talk", topic: "Why discipline beats motivation", style: "cinematic", duration: 45 },
  { id: "story", name: "History Story", description: "Calm storytelling", topic: "The story of the first computer", style: "documentary", duration: 60 },
  { id: "study", name: "Study Tips", description: "Practical tips for students", topic: "5 study habits that actually work", style: "minimal", duration: 45 },
  { id: "career", name: "Career Advice", description: "Clear advice for beginners", topic: "How to start a career in AI as a fresher", style: "modern-tech", duration: 45 },
];
