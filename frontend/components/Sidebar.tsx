"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Clapperboard, FolderOpen, LayoutDashboard, LayoutTemplate, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const ITEMS = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/dashboard" },
  { label: "Create Video", icon: Clapperboard, href: "/" },
  { label: "Projects", icon: FolderOpen, href: "/projects" },
  { label: "Templates", icon: LayoutTemplate, href: "/templates" },
  { label: "Settings", icon: Settings, href: "/settings" },
];

export default function Sidebar() {
  const path = usePathname();
  const isActive = (href: string | null) => href !== null && (href === "/" ? path === "/" : path.startsWith(href));

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="glass fixed inset-y-0 left-0 z-20 hidden w-64 flex-col rounded-none border-y-0 border-l-0 px-4 py-6 md:flex">
        <Link href="/" className="mb-8 flex items-center gap-3 px-2">
          <div className="accent-bg grid h-9 w-9 place-items-center rounded-xl">
            <Clapperboard className="h-5 w-5 text-white" aria-hidden />
          </div>
          <span className="text-base font-semibold tracking-tight">AI Video Studio</span>
        </Link>

        <nav className="flex flex-1 flex-col gap-1" aria-label="Main">
          {ITEMS.map(({ label, icon: Icon, href }) => {
            const active = isActive(href);
            const cls = cn(
              "flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition-colors",
              active ? "bg-white/10 text-white" : "text-white/55 hover:bg-white/5 hover:text-white",
            );
            return href ? (
              <Link key={label} href={href} aria-current={active ? "page" : undefined} className={cls}>
                <Icon className="h-[18px] w-[18px]" aria-hidden />
                {label}
              </Link>
            ) : (
              <span key={label} aria-disabled className={cn(cls, "cursor-not-allowed opacity-40 hover:bg-transparent hover:text-white/55")}>
                <Icon className="h-[18px] w-[18px]" aria-hidden />
                {label}
                <span className="ml-auto text-[10px] text-white/50">Soon</span>
              </span>
            );
          })}
        </nav>

        <p className="px-2 text-xs leading-relaxed text-white/40">Runs on your computer. Free tools only.</p>
      </aside>

      {/* Mobile bottom bar */}
      <nav
        aria-label="Main"
        className="glass fixed inset-x-0 bottom-0 z-20 flex justify-around rounded-none border-x-0 border-b-0 px-2 py-2 md:hidden"
      >
        {ITEMS.filter((i) => i.href).map(({ label, icon: Icon, href }) => {
          const active = isActive(href);
          return (
            <Link
              key={label}
              href={href as string}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex flex-1 flex-col items-center gap-1 rounded-lg py-1.5 text-[11px] font-medium",
                active ? "text-white" : "text-white/50",
              )}
            >
              <Icon className={cn("h-5 w-5", active && "text-violet-400")} aria-hidden />
              {label.split(" ")[0]}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
