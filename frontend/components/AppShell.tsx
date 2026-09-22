import Sidebar from "@/components/Sidebar";

// Har page ke liye common: background glow + sidebar + content width
export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen">
      <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -left-40 -top-40 h-[480px] w-[480px] rounded-full bg-violet-600/15 blur-[120px]" />
        <div className="absolute -right-32 top-1/3 h-[420px] w-[420px] rounded-full bg-sky-500/10 blur-[120px]" />
      </div>
      <Sidebar />
      <main className="pb-28 md:pb-12 md:pl-64">
        <div className="mx-auto max-w-5xl space-y-8 px-5 py-8 sm:px-8 md:py-12">{children}</div>
      </main>
    </div>
  );
}
