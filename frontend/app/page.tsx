"use client";

import { useCallback, useState } from "react";
import ErrorCard from "@/components/ErrorCard";
import PostKit from "@/components/PostKit";
import ProgressPanel from "@/components/ProgressPanel";
import SceneTimeline from "@/components/SceneTimeline";
import TopicForm from "@/components/TopicForm";
import VideoPreview from "@/components/VideoPreview";
import { useVideoJob } from "@/hooks/useVideoJob";
import { stepIndexFor } from "@/lib/config";
import type { GenerateRequest } from "@/types";

export default function Home() {
  const [request, setRequest] = useState<GenerateRequest | null>(null);
  const [activeScene, setActiveScene] = useState(0);
  const job = useVideoJob();

  const handleSceneChange = useCallback((i: number) => setActiveScene(i), []);

  function generate(r: GenerateRequest) {
    setRequest(r);
    setActiveScene(0);
    void job.start(r);
  }

  const retry = request ? () => generate(request) : undefined;

  return (
    <>
      <header>
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          <span className="accent-text">AI Video Studio</span>
        </h1>
        <p className="mt-3 text-lg text-white/60">Turn any idea into a short-form video.</p>
      </header>

      <TopicForm disabled={job.phase === "generating"} onGenerate={generate} />

      {job.phase === "generating" && (
        <ProgressPanel
          stepIndex={stepIndexFor(job.status?.status)}
          progress={job.status?.progress ?? 0}
          elapsed={job.status?.elapsed_seconds}
          typical={job.status?.typical_seconds}
        />
      )}

      {job.phase === "failed" && <ErrorCard message={job.error ?? "Please try again."} onRetry={retry} />}

      {job.phase === "done" && job.video && (
        <>
          <VideoPreview
            key={job.video.job_id}
            video={job.video}
            onRegenerate={() => retry?.()}
            onSceneChange={handleSceneChange}
          />
          <PostKit caption={job.video.caption} hashtags={job.video.hashtags} elapsed={job.video.elapsed_seconds} />
          <SceneTimeline scenes={job.video.scenes} activeIndex={activeScene} />
        </>
      )}
    </>
  );
}
