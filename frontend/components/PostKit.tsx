"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { formatTime } from "@/lib/utils";

interface Props {
  caption: string;
  hashtags: string[];
  elapsed: number | null;
}

export default function PostKit({ caption, hashtags, elapsed }: Props) {
  const [copied, setCopied] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  if (!caption && hashtags.length === 0) return null;

  const tags = hashtags.join(" ");

  async function copy(label: string, text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setFailed(false);
      setCopied(label);
      setTimeout(() => setCopied(null), 1600);
    } catch {
      setFailed(true); // clipboard block ho to user khud select karke copy kar le
    }
  }

  const btn =
    "inline-flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/[0.04] px-3.5 py-2 text-sm font-medium transition-colors hover:bg-white/10";

  return (
    <section className="reveal glass rounded-3xl p-5 sm:p-7">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">Ready to post</h2>
        {elapsed ? <span className="text-sm text-white/45">Made in {formatTime(elapsed)}</span> : null}
      </div>
      <p className="mt-1 text-sm text-white/55">A caption and hashtags written for this video. Paste them into TikTok or Facebook Reels.</p>

      <div className="mt-4 rounded-2xl border border-white/10 bg-black/30 p-4 text-sm leading-relaxed">
        {caption && <p className="select-text text-white/90">{caption}</p>}
        {tags && <p className="mt-2 select-text text-violet-300">{tags}</p>}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {caption && (
          <button type="button" className={btn} onClick={() => copy("caption", caption)}>
            {copied === "caption" ? <Check className="h-4 w-4 text-emerald-400" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />}
            Copy caption
          </button>
        )}
        {tags && (
          <button type="button" className={btn} onClick={() => copy("tags", tags)}>
            {copied === "tags" ? <Check className="h-4 w-4 text-emerald-400" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />}
            Copy hashtags
          </button>
        )}
        <button type="button" className={btn} onClick={() => copy("all", [caption, tags].filter(Boolean).join("\n\n"))}>
          {copied === "all" ? <Check className="h-4 w-4 text-emerald-400" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />}
          Copy all
        </button>
      </div>
      {failed && <p className="mt-3 text-sm text-amber-300">Could not copy automatically. Select the text above and copy it.</p>}
    </section>
  );
}
