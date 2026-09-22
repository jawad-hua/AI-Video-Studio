"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, RefreshCw, X } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import { API_BASE, getHealth } from "@/lib/api";
import type { HealthInfo } from "@/types/projects";

function Row({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <li className="flex items-center justify-between gap-4 py-3">
      <span className="text-sm text-white/65">{label}</span>
      <span className="flex min-w-0 items-center gap-2 text-sm">
        <span className="truncate text-white/90">{value}</span>
        {ok === undefined ? null : ok ? (
          <Check className="h-4 w-4 shrink-0 text-emerald-400" aria-label="OK" />
        ) : (
          <X className="h-4 w-4 shrink-0 text-red-400" aria-label="Problem" />
        )}
      </span>
    </li>
  );
}

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [brand, setBrand] = useState("");
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setHealth(await getHealth());
      setError(null);
    } catch (e) {
      setHealth(null);
      setError(e instanceof Error ? e.message : "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    try {
      setBrand(localStorage.getItem("watermark") ?? "");
    } catch {
      /* private mode: ignore */
    }
  }, []);

  function saveBrand() {
    try {
      const v = brand.trim();
      if (v) localStorage.setItem("watermark", v);
      else localStorage.removeItem("watermark");
      setSaved(true);
      setTimeout(() => setSaved(false), 1800);
    } catch {
      /* ignore */
    }
  }

  return (
    <>
      <PageHeader title="Settings" subtitle="Check that everything needed to make videos is ready." />

      <section className="glass rounded-3xl p-5 sm:p-7">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">System status</h2>
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/[0.04] px-3.5 py-2 text-sm transition-colors hover:bg-white/10 disabled:opacity-50"
          >
            <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} aria-hidden />
            Refresh
          </button>
        </div>

        <ul className="mt-3 divide-y divide-white/10">
          <Row label="Backend address" value={API_BASE} />
          <Row label="Backend" value={health ? "Connected" : error ? "Not reachable" : "Checking..."} ok={health ? true : error ? false : undefined} />
          {health && (
            <>
              <Row label="FFmpeg" value={health.ffmpeg.found ? "Installed" : "Not found"} ok={health.ffmpeg.found} />
              <Row label="Groq API key" value={health.config.groq_api_key_set ? "Set" : "Missing"} ok={health.config.groq_api_key_set} />
              <Row label="Pexels API key" value={health.config.pexels_api_key_set ? "Set" : "Missing"} ok={health.config.pexels_api_key_set} />
              <Row label="AI model" value={health.config.groq_model} />
              <Row label="Voice engine" value={health.config.tts_provider} />
              <Row label="Default video size" value={health.config.render_size} />
            </>
          )}
        </ul>

        {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
        {health && health.warnings.length > 0 && (
          <ul className="mt-4 space-y-1 text-sm text-amber-300">
            {health.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="glass rounded-3xl p-5 sm:p-7">
        <h2 className="text-lg font-semibold">Branding</h2>
        <p className="mt-1 text-sm text-white/55">
          Your handle appears softly in the top-left corner of every new video. Leave empty for no watermark.
        </p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            maxLength={30}
            placeholder="@yourchannel"
            aria-label="Watermark text"
            className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/30 px-4 py-2.5 text-sm outline-none focus:border-violet-400/60"
          />
          <button
            type="button"
            onClick={saveBrand}
            className="accent-bg rounded-xl px-5 py-2.5 text-sm font-semibold text-white transition hover:brightness-110"
          >
            {saved ? "Saved" : "Save"}
          </button>
        </div>
      </section>

      <section className="glass rounded-3xl p-5 text-sm leading-relaxed text-white/65 sm:p-7">
        <h2 className="mb-2 text-lg font-semibold text-white">How to change these</h2>
        <p>
          API keys, the AI model and the voice engine live in <code className="rounded bg-white/10 px-1.5 py-0.5">backend/.env</code>.
          Edit that file, restart the backend, then press Refresh here. Keys are never shown in the browser.
        </p>
      </section>
    </>
  );
}
