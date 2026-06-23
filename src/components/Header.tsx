import { useStore } from "../store/useStore";

const DOT: Record<string, string> = {
  connecting: "bg-amber-400 animate-pulse",
  open: "bg-emerald-400",
  closed: "bg-red-400",
};

export function Header() {
  const connection = useStore((s) => s.connection);
  const runOrder = useStore((s) => s.runOrder);

  return (
    <header className="flex items-center gap-3 border-b border-white/8 px-5 py-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-clay-500/20 ring-1 ring-clay-500/40">
        <span className="text-lg">✶</span>
      </div>
      <div>
        <h1 className="text-[15px] font-semibold tracking-tight text-stone-100">
          Claude Agentic Designer
        </h1>
        <p className="text-[11px] text-stone-500">
          Design-faithful one-pagers, white papers & decks
        </p>
      </div>

      <div className="ml-auto flex items-center gap-4 text-[11px]">
        <span className="text-stone-500">{runOrder.length} runs</span>
        <div className="flex items-center gap-1.5 rounded-full border border-white/10 bg-ink-700/60 px-2.5 py-1">
          <span className={`h-2 w-2 rounded-full ${DOT[connection]}`} />
          <span className="text-stone-300">
            {connection === "open"
              ? "Live"
              : connection === "connecting"
              ? "Connecting"
              : "Offline"}
          </span>
        </div>
      </div>
    </header>
  );
}
