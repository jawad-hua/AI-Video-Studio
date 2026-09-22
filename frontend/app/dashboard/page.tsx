"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Check, Lightbulb, Loader2, Sparkles } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import { absUrl, getHealth, getIdeas, getProjects } from "@/lib/api";
import { formatTime } from "@/lib/utils";
import type { HealthInfo, ProjectItem } from "@/types/projects";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="glass rounded-2xl p-4">
      <p className="text-sm text-white/55">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectItem[] | null>(null);
  const [health, setHealth] = useState<HealthInfo | null | undefined>(undefined); // undefined = check ho raha hai
  const [topic, setTopic] = useState("");
  const [niche, setNiche] = useState("");
  const [ideas, setIdeas] = useState<string[]>([]);
  const [ideasLoading, setIdeasLoading] = useState(false);
  const [ideasError, setIdeasError] = useState<string | null>(null);

  useEffect(() => {
    getProjects().then(setProjects).catch(() => setProjects([]));
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const stats = useMemo(() => {
    const list = projects ?? [];
    const done = list.filter((p) => p.status === "completed");
    const failed = list.filter((p) => p.status === "failed").length;
    const seconds = done.reduce((a, p) => a + (p.duration ?? 0), 0);
    const times = done.map((p) => p.elapsed_seconds).filter((x): x is number => typeof x === "number");
    const avg = times.length ? times.reduce((a, b) => a + b, 0) / times.length : null;
    const finished = done.length + failed;
    return {
      videos: done.length,
      minutes: seconds / 60,
      avg,
      success: finished ? Math.round((done.length / finished) * 100) : null,
      recent: done.slice(0, 3),
    };
  }, [projects]);

  function create(t: string) {
    if (t.trim().length < 5) return;
    sessionStorage.setItem("template", JSON.stringify({ topic: t.trim() })); // Create Video page form bhar dega
    router.push("/");
  }

  async function fetchIdeas() {
    setIdeasLoading(true);
    setIdeasError(null);
    try {
      setIdeas((await getIdeas(niche)).ideas);
    } catch (e) {
      setIdeasError(e instanceof Error ? e.message : "Could not get ideas.");
    } finally {
      setIdeasLoading(false);
    }
  }

  const loaded = projects !== null;

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Your studio at a glance." />

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Statistics">
        <Stat label="Videos created" value={loaded ? String(stats.videos) : "-"} />
        <Stat label="Total video length" value={loaded ? `${stats.minutes.toFixed(1)} min` : "-"} />
        <Stat label="Average creation time" value={stats.avg ? formatTime(stats.avg) : "-"} />
        <Stat label="Success rate" value={stats.success !== null ? `${stats.success}%` : "-"} />
      </section>

      <section className="glass rounded-3xl p-5 sm:p-7">
        <h2 className="text-lg font-semibold">Quick create</h2>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && create(topic)}
            placeholder="What is your next video about?"
            aria-label="Video topic"
            className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/30 px-4 py-3 outline-none placeholder:text-white/30 focus:border-violet-400/60"
          />
          <button
            type="button"
            onClick={() => create(topic)}
            disabled={topic.trim().length < 5}
            className="accent-bg inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Sparkles className="h-4 w-4" aria-hidden />
            Create video
          </button>
        </div>

        <div className="mt-6 border-t border-white/10 pt-5">
          <h3 className="flex items-center gap-2 text-sm font-medium text-white/80">
            <Lightbulb className="h-4 w-4 text-amber-300" aria-hidden />
            Need an idea?
          </h3>
          <div className="mt-3 flex flex-col gap-3 sm:flex-row">
            <input
              value={niche}
              onChange={(e) => setNiche(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void fetchIdeas()}
              maxLength={60}
              placeholder="Your niche, e.g. fitness, AI tools, cooking (optional)"
              aria-label="Niche"
              className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/30 px-4 py-2.5 text-sm outline-none placeholder:text-white/30 focus:border-violet-400/60"
            />
            <button
              type="button"
              onClick={() => void fetchIdeas()}
              disabled={ideasLoading}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/[0.04] px-4 py-2.5 text-sm font-medium transition-colors hover:bg-white/10 disabled:opacity-50"
            >
              {ideasLoading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
              Get ideas
            </button>
          </div>
          {ideasError && <p className="mt-3 text-sm text-red-300">{ideasError}</p>}
          {ideas.length > 0 && (
            <ul className="mt-4 flex flex-wrap gap-2">
              {ideas.map((idea) => (
                <li key={idea}>
                  <button
                    type="button"
                    onClick={() => setTopic(idea)}
                    className="rounded-full border border-white/10 bg-white/[0.03] px-3.5 py-1.5 text-left text-sm text-white/75 transition-colors hover:border-violet-400/50 hover:text-white"
                  >
                    {idea}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent videos</h2>
          <Link href="/projects" className="text-sm text-violet-300 hover:text-violet-200">
            View all
          </Link>
        </div>
        {loaded && stats.recent.length === 0 ? (
          <p className="glass rounded-2xl p-5 text-sm text-white/55">No videos yet. Create your first one above.</p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-3">
            {stats.recent.map((p) => (
              <li key={p.job_id}>
                <Link href="/projects" className="glass flex gap-3 rounded-2xl p-3 transition-colors hover:bg-white/[0.07]">
                  <div className="aspect-[9/16] w-14 shrink-0 overflow-hidden rounded-lg bg-white/10">
                    {p.thumbnail_url && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={absUrl(p.thumbnail_url)} alt="" loading="lazy" className="h-full w-full object-cover" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="line-clamp-2 text-sm font-medium">{p.title}</p>
                    <p className="mt-1 text-xs text-white/50">{p.duration ? formatTime(p.duration) : ""}</p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="glass flex items-start gap-3 rounded-2xl p-4 text-sm">
        {health === undefined ? (
          <p className="text-white/55">Checking system...</p>
        ) : health && health.warnings.length === 0 ? (
          <>
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" aria-hidden />
            <p className="text-white/70">Everything is ready. FFmpeg and both API keys are set.</p>
          </>
        ) : (
          <>
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" aria-hidden />
            <p className="text-white/70">
              {health ? health.warnings[0] : "The backend is not reachable."}{" "}
              <Link href="/settings" className="text-violet-300 hover:text-violet-200">
                Open Settings
              </Link>
            </p>
          </>
        )}
      </section>
    </>
  );
}
