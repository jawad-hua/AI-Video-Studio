"use client";

import { useState } from "react";
import { Download, Loader2, Play, Trash2 } from "lucide-react";
import { absUrl } from "@/lib/api";
import { STYLES } from "@/lib/config";
import { formatTime } from "@/lib/utils";
import type { ProjectItem } from "@/types/projects";

interface Props {
  item: ProjectItem;
  onDelete: (item: ProjectItem) => void;
}

export default function ProjectCard({ item, onDelete }: Props) {
  const [playing, setPlaying] = useState(false);
  const [thumbFailed, setThumbFailed] = useState(false);
  const running = item.status !== "completed" && item.status !== "failed";
  const styleLabel = STYLES.find((s) => s.id === item.style)?.label ?? item.style;
  const date = new Date(item.created_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });

  return (
    <li className="glass flex flex-col gap-4 rounded-2xl p-4">
      <div className="flex gap-4">
        <div className="relative grid aspect-[9/16] w-20 shrink-0 place-items-center overflow-hidden rounded-xl bg-white/10">
          {item.thumbnail_url && !thumbFailed ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={absUrl(item.thumbnail_url)}
              alt=""
              loading="lazy"
              onError={() => setThumbFailed(true)}
              className="h-full w-full object-cover"
            />
          ) : running ? (
            <Loader2 className="h-5 w-5 animate-spin text-white/60" aria-hidden />
          ) : null}
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="line-clamp-2 font-semibold leading-snug">{item.title}</h3>
          <p className="mt-1 line-clamp-2 text-sm text-white/55">{item.topic}</p>
          <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-white/60">
            <span className="rounded-full bg-white/10 px-2 py-0.5">{styleLabel}</span>
            {item.duration !== null && (
              <span className="rounded-full bg-white/10 px-2 py-0.5">{formatTime(item.duration)}</span>
            )}
            {item.elapsed_seconds ? (
              <span className="rounded-full bg-white/10 px-2 py-0.5">Made in {formatTime(item.elapsed_seconds)}</span>
            ) : null}
            <span className="rounded-full bg-white/10 px-2 py-0.5">{date}</span>
          </div>
        </div>
      </div>

      {item.status === "failed" && (
        <p className="rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-300">{item.error ?? "This video failed."}</p>
      )}
      {running && <p className="text-sm text-violet-300">Still being made...</p>}

      {playing && item.video_url && (
        <video
          src={absUrl(item.video_url)}
          controls
          autoPlay
          playsInline
          className="mx-auto aspect-[9/16] w-full max-w-[240px] rounded-2xl bg-black object-cover"
        />
      )}

      <div className="flex flex-wrap gap-2">
        {item.video_url && (
          <button
            type="button"
            onClick={() => setPlaying((p) => !p)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/[0.04] px-3.5 py-2 text-sm font-medium transition-colors hover:bg-white/10"
          >
            <Play className="h-4 w-4" aria-hidden />
            {playing ? "Close" : "Watch"}
          </button>
        )}
        {item.download_url && (
          <a
            href={absUrl(item.download_url)}
            download
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/[0.04] px-3.5 py-2 text-sm font-medium transition-colors hover:bg-white/10"
          >
            <Download className="h-4 w-4" aria-hidden />
            Download
          </a>
        )}
        {!running && (
          <button
            type="button"
            onClick={() => onDelete(item)}
            className="ml-auto inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm text-white/50 transition-colors hover:bg-red-500/10 hover:text-red-300"
          >
            <Trash2 className="h-4 w-4" aria-hidden />
            Delete
          </button>
        )}
      </div>
    </li>
  );
}
