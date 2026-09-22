"use client";

import { useRouter } from "next/navigation";
import PageHeader from "@/components/PageHeader";
import { STYLES } from "@/lib/config";
import { TEMPLATES, type Template } from "@/lib/templates";

export default function TemplatesPage() {
  const router = useRouter();

  function use(t: Template) {
    // Create Video page isse padh kar form bhar deta hai
    sessionStorage.setItem("template", JSON.stringify({ topic: t.topic, style: t.style, duration: t.duration }));
    router.push("/");
  }

  return (
    <>
      <PageHeader title="Templates" subtitle="Pick a starting point. You can edit everything before generating." />
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {TEMPLATES.map((t) => (
          <li key={t.id} className="glass flex flex-col rounded-2xl p-5">
            <h2 className="font-semibold">{t.name}</h2>
            <p className="mt-1 text-sm text-white/55">{t.description}</p>
            <p className="mt-3 flex-1 text-sm text-white/80">&ldquo;{t.topic}&rdquo;</p>
            <div className="mt-4 flex flex-wrap gap-1.5 text-xs text-white/60">
              <span className="rounded-full bg-white/10 px-2 py-0.5">
                {STYLES.find((s) => s.id === t.style)?.label}
              </span>
              <span className="rounded-full bg-white/10 px-2 py-0.5">{t.duration} sec</span>
            </div>
            <button
              type="button"
              onClick={() => use(t)}
              className="accent-bg mt-4 rounded-xl px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110"
            >
              Use template
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
