"use client";

import { useEffect, useState } from "react";
import { ChevronDown, Smartphone, Sparkles } from "lucide-react";
import Segmented from "@/components/ui/Segmented";
import { EXAMPLES, STYLES, VOICES } from "@/lib/config";
import { cn } from "@/lib/utils";
import type { GenerateRequest, Resolution, VideoStyle } from "@/types";

// Settings page mein save kiya hua brand handle (sirf is browser mein)
function readWatermark(): string | null {
  try {
    return localStorage.getItem("watermark")?.trim() || null;
  } catch {
    return null;
  }
}

interface Props {
  disabled: boolean;
  onGenerate: (request: GenerateRequest) => void;
}

export default function TopicForm({ disabled, onGenerate }: Props) {
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState<30 | 45 | 60>(60);
  const [style, setStyle] = useState<VideoStyle>("modern-tech");
  const [voice, setVoice] = useState(VOICES[0].id);
  const [resolution, setResolution] = useState<Resolution>("720p");
  const [music, setMusic] = useState(true);
  const [speed, setSpeed] = useState<"fast" | "balanced">("fast");
  const [sfx, setSfx] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Templates page se aaya ho to topic/style/duration pehle se bhar do
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("template");
      if (!raw) return;
      sessionStorage.removeItem("template");
      const t = JSON.parse(raw);
      if (typeof t.topic === "string") setTopic(t.topic);
      if (STYLES.some((s) => s.id === t.style)) setStyle(t.style);
      if ([30, 45, 60].includes(t.duration)) setDuration(t.duration);
    } catch {
      /* kharab data ignore */
    }
  }, []);

  const canSubmit = topic.trim().length >= 5 && !disabled;

  function submit() {
    if (!canSubmit) return;
    onGenerate({
      topic: topic.trim(),
      duration,
      aspect_ratio: "9:16",
      style,
      voice,
      resolution,
      background_music: music,
      speed,
      sound_effects: sfx,
      watermark: readWatermark(),
    });
  }

  return (
    <section className="glass rounded-3xl p-5 sm:p-7">
      <label htmlFor="topic" className="mb-2 block text-sm font-medium text-white/70">
        What is your video about?
      </label>
      <textarea
        id="topic"
        rows={3}
        value={topic}
        disabled={disabled}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="Describe your video topic..."
        className="w-full resize-none rounded-2xl border border-white/10 bg-black/30 p-4 text-lg leading-relaxed text-white outline-none transition-colors placeholder:text-white/30 focus:border-violet-400/60 disabled:opacity-60"
      />

      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            disabled={disabled}
            onClick={() => setTopic(ex)}
            className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-white/60 transition-colors hover:border-white/25 hover:text-white disabled:opacity-50"
          >
            {ex}
          </button>
        ))}
      </div>

      <div className="mt-7 grid gap-6 md:grid-cols-3">
        <div>
          <p className="mb-2 text-sm font-medium text-white/70">Video duration</p>
          <Segmented
            label="Video duration"
            disabled={disabled}
            value={duration}
            onChange={setDuration}
            options={[
              { value: 30, label: "30 sec" },
              { value: 45, label: "45 sec" },
              { value: 60, label: "60 sec" },
            ]}
          />
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-white/70">Aspect ratio</p>
          <button
            type="button"
            aria-pressed="true"
            className="accent-bg inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white"
          >
            <Smartphone className="h-4 w-4" aria-hidden />
            9:16 Vertical
          </button>
        </div>

        <div>
          <label htmlFor="voice" className="mb-2 block text-sm font-medium text-white/70">
            Voice
          </label>
          <select
            id="voice"
            value={voice}
            disabled={disabled}
            onChange={(e) => setVoice(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none focus:border-violet-400/60 disabled:opacity-60"
          >
            {VOICES.map((v) => (
              <option key={v.id} value={v.id} className="bg-neutral-900">
                {v.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-6">
        <p className="mb-2 text-sm font-medium text-white/70">Style</p>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" role="radiogroup" aria-label="Style">
          {STYLES.map((s) => {
            const active = s.id === style;
            return (
              <button
                key={s.id}
                type="button"
                role="radio"
                aria-checked={active}
                disabled={disabled}
                onClick={() => setStyle(s.id)}
                className={cn(
                  "rounded-2xl border p-3.5 text-left transition-colors disabled:opacity-60",
                  active
                    ? "border-violet-400/70 bg-violet-500/10"
                    : "border-white/10 bg-white/[0.02] hover:border-white/25",
                )}
              >
                <span className="block text-sm font-semibold">{s.label}</span>
                <span className="mt-0.5 block text-xs text-white/50">{s.hint}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-6">
        <button
          type="button"
          aria-expanded={showAdvanced}
          onClick={() => setShowAdvanced((v) => !v)}
          className="inline-flex items-center gap-1.5 text-sm text-white/55 transition-colors hover:text-white"
        >
          Advanced settings
          <ChevronDown
            className={cn("h-4 w-4 transition-transform", showAdvanced && "rotate-180")}
            aria-hidden
          />
        </button>

        {showAdvanced && (
          <div className="mt-4 grid gap-5 rounded-2xl border border-white/10 bg-black/20 p-4 sm:grid-cols-2">
            <div>
              <p className="mb-2 text-sm font-medium text-white/70">Quality</p>
              <Segmented
                label="Quality"
                disabled={disabled}
                value={resolution}
                onChange={setResolution}
                options={[
                  { value: "720p", label: "720p (fast)" },
                  { value: "1080p", label: "1080p (HD)" },
                ]}
              />
              <p className="mt-2 text-xs text-white/40">
                Use 720p on low-RAM laptops. 1080p renders slower.
              </p>
            </div>

            <div>
              <p className="mb-2 text-sm font-medium text-white/70">Background music</p>
              <button
                type="button"
                role="switch"
                aria-checked={music}
                aria-label="Background music"
                disabled={disabled}
                onClick={() => setMusic((v) => !v)}
                className={cn(
                  "relative h-7 w-12 rounded-full transition-colors disabled:opacity-60",
                  music ? "accent-bg" : "bg-white/15",
                )}
              >
                <span
                  className={cn(
                    "absolute top-1 h-5 w-5 rounded-full bg-white transition-all",
                    music ? "left-6" : "left-1",
                  )}
                />
              </button>
              <p className="mt-2 text-xs text-white/40">Picks a track from your music folder.</p>
            </div>

            <div>
              <p className="mb-2 text-sm font-medium text-white/70">Render speed</p>
              <Segmented
                label="Render speed"
                disabled={disabled}
                value={speed}
                onChange={setSpeed}
                options={[
                  { value: "fast", label: "Fast" },
                  { value: "balanced", label: "Balanced" },
                ]}
              />
              <p className="mt-2 text-xs text-white/40">Fast is about 2x quicker. Balanced adds a soft vignette and sharper encode.</p>
            </div>

            <div>
              <p className="mb-2 text-sm font-medium text-white/70">Transition sounds</p>
              <button
                type="button"
                role="switch"
                aria-checked={sfx}
                aria-label="Transition sounds"
                disabled={disabled}
                onClick={() => setSfx((v) => !v)}
                className={cn(
                  "relative h-7 w-12 rounded-full transition-colors disabled:opacity-60",
                  sfx ? "accent-bg" : "bg-white/15",
                )}
              >
                <span
                  className={cn(
                    "absolute top-1 h-5 w-5 rounded-full bg-white transition-all",
                    sfx ? "left-6" : "left-1",
                  )}
                />
              </button>
              <p className="mt-2 text-xs text-white/40">A soft whoosh on every scene change.</p>
            </div>
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={submit}
        disabled={!canSubmit}
        className="accent-bg mt-7 inline-flex w-full items-center justify-center gap-2 rounded-2xl px-6 py-3.5 text-base font-semibold text-white shadow-lg shadow-violet-500/20 transition hover:brightness-110 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto"
      >
        <Sparkles className="h-5 w-5" aria-hidden />
        Generate Video
      </button>
    </section>
  );
}
