"use client";

import { useEffect, useRef, useState } from "react";
import { Download, Pause, Play, RefreshCw } from "lucide-react";
import { absUrl } from "@/lib/api";
import { STYLES } from "@/lib/config";
import { formatTime } from "@/lib/utils";
import type { VideoInfo } from "@/types";

interface Props {
  video: VideoInfo;
  onRegenerate: () => void;
  onSceneChange: (index: number) => void;
}

export default function VideoPreview({ video, onRegenerate, onSceneChange }: Props) {
  const ref = useRef<HTMLVideoElement>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const total = video.duration;

  // Abhi kaunsa scene chal raha hai (timeline mein highlight ke liye)
  let idx = video.scenes.length - 1;
  for (let i = 0; i < video.scenes.length; i++) {
    if (t < video.scenes[i].start + video.scenes[i].duration) {
      idx = i;
      break;
    }
  }
  useEffect(() => {
    onSceneChange(idx);
  }, [idx, onSceneChange]);

  function toggle() {
    const el = ref.current;
    if (!el) return;
    if (el.paused) el.play().catch(() => {});
    else el.pause();
  }

  function seek(e: React.MouseEvent<HTMLDivElement>) {
    const el = ref.current;
    if (!el) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    el.currentTime = ratio * total;
    setT(ratio * total);
  }

  const styleLabel = STYLES.find((s) => s.id === video.style)?.label ?? video.style;
  const poster = video.scenes[0] ? absUrl(video.scenes[0].thumbnail_url) : undefined;

  return (
    <section className="reveal glass grid gap-8 rounded-3xl p-5 sm:p-7 lg:grid-cols-[300px_1fr]">
      {/* Vertical player: subtitles video mein pehle se burn hain */}
      <div>
        <div className="relative mx-auto aspect-[9/16] w-full max-w-[280px] overflow-hidden rounded-[28px] border border-white/10 bg-black shadow-2xl shadow-black/60">
          <video
            ref={ref}
            src={absUrl(video.video_url)}
            poster={poster}
            playsInline
            preload="metadata"
            onClick={toggle}
            onTimeUpdate={(e) => setT(e.currentTarget.currentTime)}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
            className="absolute inset-0 h-full w-full cursor-pointer object-cover"
          />

          {!playing && (
            <button
              type="button"
              onClick={toggle}
              aria-label="Play"
              className="absolute inset-0 grid place-items-center"
            >
              <span className="grid h-16 w-16 place-items-center rounded-full bg-black/45 backdrop-blur">
                <Play className="ml-1 h-7 w-7 text-white" aria-hidden />
              </span>
            </button>
          )}

          <div className="absolute inset-x-4 bottom-4 flex items-center gap-2">
            <button
              type="button"
              onClick={toggle}
              aria-label={playing ? "Pause" : "Play"}
              className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-black/45 backdrop-blur"
            >
              {playing ? <Pause className="h-4 w-4" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}
            </button>
            <div
              role="slider"
              tabIndex={0}
              aria-label="Seek"
              aria-valuemin={0}
              aria-valuemax={Math.round(total)}
              aria-valuenow={Math.round(t)}
              onClick={seek}
              className="h-1.5 flex-1 cursor-pointer rounded-full bg-white/25"
            >
              <div className="h-full rounded-full bg-white" style={{ width: `${Math.min(100, (t / total) * 100)}%` }} />
            </div>
            <span className="w-16 shrink-0 text-right text-[11px] tabular-nums text-white/80">
              {formatTime(t)} / {formatTime(total)}
            </span>
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="flex flex-col justify-center">
        <p className="text-sm text-white/50">Your video is ready</p>
        <h2 className="mt-1 text-2xl font-semibold leading-snug sm:text-3xl">{video.title}</h2>

        <div className="mt-5 flex flex-wrap gap-2 text-sm">
          {[
            `${formatTime(total)} long`,
            `${video.scenes.length} scenes`,
            styleLabel,
            `${video.width} x ${video.height}`,
            `${video.size_mb} MB`,
          ].map((b) => (
            <span key={b} className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-white/70">
              {b}
            </span>
          ))}
        </div>

        <div className="mt-7 flex flex-wrap gap-3">
          <a
            href={absUrl(video.download_url)}
            download
            className="accent-bg inline-flex items-center gap-2 rounded-2xl px-5 py-3 font-semibold text-white shadow-lg shadow-violet-500/20 transition hover:brightness-110"
          >
            <Download className="h-5 w-5" aria-hidden />
            Download MP4
          </a>
          <button
            type="button"
            onClick={onRegenerate}
            className="inline-flex items-center gap-2 rounded-2xl border border-white/15 bg-white/[0.04] px-5 py-3 font-medium text-white/90 transition-colors hover:bg-white/10"
          >
            <RefreshCw className="h-5 w-5" aria-hidden />
            Regenerate
          </button>
        </div>
      </div>
    </section>
  );
}
