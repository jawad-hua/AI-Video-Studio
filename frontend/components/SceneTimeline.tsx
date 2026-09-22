"use client";

import { useState } from "react";
import { Film, Image as ImageIcon, ImageOff } from "lucide-react";
import { absUrl } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { SceneInfo } from "@/types";

interface Props {
  scenes: SceneInfo[];
  activeIndex: number;
}

function sourceLabel(scene: SceneInfo) {
  if (scene.media_source === "fallback") return { text: "Placeholder (no match)", Icon: ImageOff };
  return scene.media_type === "video"
    ? { text: "Pexels video", Icon: Film }
    : { text: "Pexels image", Icon: ImageIcon };
}

function Thumb({ scene }: { scene: SceneInfo }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className="grid aspect-[9/16] w-16 shrink-0 place-items-center overflow-hidden rounded-xl bg-white/10 text-sm font-bold text-white/70">
      {failed ? (
        scene.number
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={absUrl(scene.thumbnail_url)}
          alt={`Scene ${scene.number} preview`}
          loading="lazy"
          onError={() => setFailed(true)}
          className="h-full w-full object-cover"
        />
      )}
    </div>
  );
}

export default function SceneTimeline({ scenes, activeIndex }: Props) {
  return (
    <section className="reveal">
      <h2 className="mb-4 text-lg font-semibold">Scene timeline</h2>
      <ol className="grid gap-3 md:grid-cols-2">
        {scenes.map((scene, i) => {
          const { text, Icon } = sourceLabel(scene);
          return (
            <li
              key={scene.number}
              className={cn(
                "glass flex gap-4 rounded-2xl p-3.5 transition-colors",
                i === activeIndex && "border-violet-400/60 bg-violet-500/[0.07]",
              )}
            >
              <Thumb scene={scene} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold">Scene {String(scene.number).padStart(2, "0")}</h3>
                  <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs tabular-nums text-white/70">
                    {scene.duration.toFixed(1)}s
                  </span>
                </div>
                <p className="mt-1.5 line-clamp-3 text-sm leading-relaxed text-white/65">{scene.narration}</p>
                <p className="mt-2 inline-flex items-center gap-1.5 text-xs text-white/45">
                  <Icon className="h-3.5 w-3.5" aria-hidden />
                  {text}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
