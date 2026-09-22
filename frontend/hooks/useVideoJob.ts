"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, createJob, getStatus, getVideo } from "@/lib/api";
import type { GenerateRequest, StatusResponse, VideoInfo } from "@/types";

const POLL_MS = 2000;
const MAX_NETWORK_FAILS = 3; // itni baar lagatar server na mile to error dikhao

export type Phase = "idle" | "generating" | "done" | "failed";

const messageOf = (e: unknown) =>
  e instanceof Error ? e.message : "Something went wrong. Please try again.";

export function useVideoJob() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [video, setVideo] = useState<VideoInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  const token = useRef(0); // naya job shuru ho to purani polling khud ruk jati hai
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancel = useCallback(() => {
    token.current += 1;
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  }, []);

  useEffect(() => cancel, [cancel]); // page band ho to polling band

  const start = useCallback(
    async (req: GenerateRequest) => {
      cancel();
      const mine = token.current;
      setPhase("generating");
      setStatus(null);
      setVideo(null);
      setError(null);

      const fail = (msg: string) => {
        if (token.current !== mine) return;
        setError(msg);
        setPhase("failed");
      };

      let jobId: string;
      try {
        jobId = (await createJob(req)).job_id;
      } catch (e) {
        fail(messageOf(e));
        return;
      }

      let networkFails = 0;
      const tick = async () => {
        if (token.current !== mine) return;
        try {
          const s = await getStatus(jobId);
          if (token.current !== mine) return;
          networkFails = 0;
          setStatus(s);

          if (s.status === "completed") {
            const v = await getVideo(jobId);
            if (token.current !== mine) return;
            setVideo(v);
            setPhase("done");
            return;
          }
          if (s.status === "failed") {
            fail(s.error ?? "Video generation failed. Please try again.");
            return;
          }
        } catch (e) {
          // 0 = server nahi mila, 5xx = server ka temporary masla: dobara koshish karo
          if (e instanceof ApiError && (e.status === 0 || e.status >= 500)) {
            networkFails += 1;
            if (networkFails >= MAX_NETWORK_FAILS) {
              fail(messageOf(e));
              return;
            }
          } else {
            fail(messageOf(e));
            return;
          }
        }
        timer.current = setTimeout(tick, POLL_MS);
      };
      void tick();
    },
    [cancel],
  );

  return { phase, status, video, error, start };
}
