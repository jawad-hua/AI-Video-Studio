import { AlertTriangle, RotateCcw } from "lucide-react";

interface Props {
  message: string;
  onRetry?: () => void;
}

export default function ErrorCard({ message, onRetry }: Props) {
  return (
    <section role="alert" className="reveal glass flex flex-col gap-4 rounded-3xl border-red-400/30 p-5 sm:flex-row sm:items-center sm:p-7">
      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-red-500/15">
        <AlertTriangle className="h-5 w-5 text-red-400" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <h2 className="text-base font-semibold">Could not create the video</h2>
        <p className="mt-1 text-sm text-white/65">{message}</p>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/15 bg-white/[0.04] px-5 py-2.5 text-sm font-medium transition-colors hover:bg-white/10"
        >
          <RotateCcw className="h-4 w-4" aria-hidden />
          Try again
        </button>
      )}
    </section>
  );
}
