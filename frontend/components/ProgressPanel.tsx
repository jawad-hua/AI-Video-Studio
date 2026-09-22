import { Check, Circle, Loader2 } from "lucide-react";
import { STEPS } from "@/lib/config";
import { cn, formatTime } from "@/lib/utils";
import type { StepState } from "@/types";

interface Props {
  stepIndex: number;
  progress: number;
  elapsed?: number;
  typical?: number | null;
}

export default function ProgressPanel({ stepIndex, progress, elapsed, typical }: Props) {
  return (
    <section className="glass rounded-3xl p-5 sm:p-7" aria-live="polite">
      <div className="mb-4 flex items-end justify-between">
        <h2 className="text-lg font-semibold">Creating your video</h2>
        <span className="text-sm tabular-nums text-white/60">{progress}%</span>
      </div>

      <div
        className="h-2 overflow-hidden rounded-full bg-white/10"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="accent-bg h-full rounded-full transition-[width] duration-200"
          style={{ width: `${progress}%` }}
        />
      </div>

      {elapsed !== undefined && (
        <p className="mt-3 text-sm text-white/50">
          Elapsed {formatTime(elapsed)}.{typical ? ` Usually takes about ${formatTime(typical)} on this computer.` : ""}
        </p>
      )}

      <ul className="mt-6 grid gap-3 sm:grid-cols-2">
        {STEPS.map((step, i) => {
          const state: StepState = i < stepIndex ? "done" : i === stepIndex ? "active" : "pending";
          return (
            <li
              key={step.id}
              className={cn(
                "flex items-center gap-3 text-sm transition-colors",
                state === "done" && "text-white",
                state === "active" && "text-violet-300",
                state === "pending" && "text-white/35",
              )}
            >
              {state === "done" && (
                <span className="grid h-6 w-6 place-items-center rounded-full bg-emerald-500/20">
                  <Check className="h-3.5 w-3.5 text-emerald-400" aria-hidden />
                </span>
              )}
              {state === "active" && (
                <span className="grid h-6 w-6 place-items-center">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                </span>
              )}
              {state === "pending" && (
                <span className="grid h-6 w-6 place-items-center">
                  <Circle className="h-3.5 w-3.5" aria-hidden />
                </span>
              )}
              {state === "done" ? step.doneLabel : step.activeLabel}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
