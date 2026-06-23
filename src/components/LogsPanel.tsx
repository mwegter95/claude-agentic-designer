import { useEffect, useMemo, useRef, useState } from "react";
import { AGENT_META, MAX_LOGS } from "../config";
import { useStore } from "../store/useStore";
import type { AgentEvent, LogLevel } from "../types";

const LEVEL_COLOR: Record<LogLevel, string> = {
  debug: "text-stone-500",
  info: "text-stone-300",
  warn: "text-amber-300",
  error: "text-red-400",
};

const TYPE_BADGE: Record<string, string> = {
  run_start: "bg-clay-600/30 text-clay-300",
  run_end: "bg-clay-600/30 text-clay-300",
  agent_start: "bg-sky-500/20 text-sky-300",
  agent_end: "bg-sky-500/20 text-sky-300",
  agent_thinking: "bg-violet-500/20 text-violet-300",
  tool_call: "bg-emerald-500/20 text-emerald-300",
  tool_result: "bg-emerald-500/20 text-emerald-300",
  evaluation: "bg-amber-500/20 text-amber-300",
  artifact: "bg-pink-500/20 text-pink-300",
  iteration: "bg-orange-500/20 text-orange-300",
  log: "bg-ink-500 text-stone-400",
};

function ts(t: number) {
  const d = new Date(t * 1000);
  return d.toLocaleTimeString("en-US", { hour12: false }) +
    "." + String(d.getMilliseconds()).padStart(3, "0");
}

function LogRow({ ev }: { ev: AgentEvent }) {
  const [open, setOpen] = useState(false);
  const hasData = ev.data && Object.keys(ev.data).length > 0;
  const meta = ev.agent ? AGENT_META[ev.agent] : null;
  return (
    <div className="animate-fadeIn border-b border-white/5 px-2 py-1 font-mono text-[11px] leading-relaxed hover:bg-white/5">
      <div className="flex items-start gap-2">
        <span className="shrink-0 text-stone-600">{ts(ev.ts)}</span>
        {meta ? (
          <span
            className="shrink-0 rounded px-1 font-bold"
            style={{ color: meta.color }}
          >
            {meta.short}
          </span>
        ) : (
          <span className="shrink-0 text-stone-600">···</span>
        )}
        <span
          className={`shrink-0 rounded px-1 text-[9px] uppercase tracking-wide ${
            TYPE_BADGE[ev.type] ?? "bg-ink-500 text-stone-400"
          }`}
        >
          {ev.type.replace("_", " ")}
        </span>
        <button
          onClick={() => hasData && setOpen((o) => !o)}
          className={`text-left ${LEVEL_COLOR[ev.level]} ${
            hasData ? "cursor-pointer hover:underline" : "cursor-default"
          }`}
        >
          {ev.message || <span className="italic text-stone-600">(no message)</span>}
          {hasData && <span className="ml-1 text-stone-600">{open ? "▾" : "▸"}</span>}
        </button>
      </div>
      {open && hasData && (
        <pre className="mt-1 ml-16 overflow-x-auto rounded bg-ink-900/70 p-2 text-[10px] text-stone-400">
          {JSON.stringify(ev.data, null, 2)}
        </pre>
      )}
    </div>
  );
}

export function LogsPanel() {
  const selectedRunId = useStore((s) => s.selectedRunId);
  const run = useStore((s) => (selectedRunId ? s.runs[selectedRunId] : undefined));
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState("");
  const [levelMin, setLevelMin] = useState<LogLevel | "all">("all");
  const bottomRef = useRef<HTMLDivElement>(null);

  const events = run?.events ?? [];

  const filtered = useMemo(() => {
    const order: LogLevel[] = ["debug", "info", "warn", "error"];
    const min = levelMin === "all" ? 0 : order.indexOf(levelMin);
    const q = filter.trim().toLowerCase();
    return events.filter((e) => {
      if (order.indexOf(e.level) < min) return false;
      if (!q) return true;
      return (
        e.message.toLowerCase().includes(q) ||
        (e.agent ?? "").includes(q) ||
        e.type.includes(q)
      );
    });
  }, [events, filter, levelMin]);

  useEffect(() => {
    if (autoScroll) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [filtered.length, autoScroll]);

  return (
    <div className="flex h-full flex-col rounded-2xl border border-white/8 bg-ink-800/50">
      <div className="flex items-center gap-2 border-b border-white/8 px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-widest text-stone-400">
          Logs
        </span>
        <span className="rounded-full bg-ink-600 px-2 py-0.5 text-[10px] text-stone-400">
          {events.length}/{MAX_LOGS}
        </span>
        <div className="ml-auto flex items-center gap-2">
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="filter…"
            className="w-28 rounded-md border border-white/10 bg-ink-700 px-2 py-1 text-[11px] text-stone-200 outline-none focus:border-clay-500"
          />
          <select
            value={levelMin}
            onChange={(e) => setLevelMin(e.target.value as LogLevel | "all")}
            className="rounded-md border border-white/10 bg-ink-700 px-1.5 py-1 text-[11px] text-stone-300 outline-none"
          >
            <option value="all">all</option>
            <option value="debug">debug+</option>
            <option value="info">info+</option>
            <option value="warn">warn+</option>
            <option value="error">error</option>
          </select>
          <button
            onClick={() => setAutoScroll((a) => !a)}
            className={`rounded-md px-2 py-1 text-[11px] ${
              autoScroll
                ? "bg-clay-600/30 text-clay-300"
                : "bg-ink-600 text-stone-400"
            }`}
            title="Auto-scroll to newest"
          >
            ↓ auto
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-stone-600">
            {events.length === 0
              ? "Waiting for agent activity…"
              : "No logs match the filter."}
          </div>
        ) : (
          <>
            {filtered.map((ev) => (
              <LogRow key={`${ev.run_id}-${ev.seq}-${ev.ts}`} ev={ev} />
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  );
}
