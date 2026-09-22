"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import PageHeader from "@/components/PageHeader";
import ProjectCard from "@/components/ProjectCard";
import ErrorCard from "@/components/ErrorCard";
import { deleteProject, getProjects } from "@/lib/api";
import type { ProjectItem } from "@/types/projects";

export default function ProjectsPage() {
  const [items, setItems] = useState<ProjectItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await getProjects());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load projects.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Koi video ban rahi ho to har 4 sec list refresh
  const hasRunning = items?.some((i) => i.status !== "completed" && i.status !== "failed");
  useEffect(() => {
    if (!hasRunning) return;
    const id = setInterval(() => void load(), 4000);
    return () => clearInterval(id);
  }, [hasRunning, load]);

  async function remove(item: ProjectItem) {
    if (!window.confirm(`Delete "${item.title}"? This removes the video and its files.`)) return;
    try {
      await deleteProject(item.job_id);
      setItems((prev) => prev?.filter((i) => i.job_id !== item.job_id) ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete the video.");
    }
  }

  return (
    <>
      <PageHeader title="Projects" subtitle="Your generated videos. Watch, download or delete them." />

      {error && <ErrorCard message={error} onRetry={() => void load()} />}

      {items === null && !error && <p className="text-white/50">Loading...</p>}

      {items?.length === 0 && (
        <div className="glass rounded-3xl p-8 text-center">
          <p className="text-white/70">No videos yet.</p>
          <Link href="/" className="accent-bg mt-4 inline-block rounded-2xl px-5 py-2.5 font-semibold text-white">
            Create your first video
          </Link>
        </div>
      )}

      {items && items.length > 0 && (
        <ul className="grid gap-4 md:grid-cols-2">
          {items.map((item) => (
            <ProjectCard key={item.job_id} item={item} onDelete={remove} />
          ))}
        </ul>
      )}
    </>
  );
}
