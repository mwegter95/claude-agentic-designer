import { AGENT_META } from "../config";
import type { AgentId, AgentStatus } from "../types";

interface Props {
  agentId: AgentId;
  status: AgentStatus;
  isCurrent: boolean;
  message?: string;
}

const STATUS_DOT: Record<AgentStatus, string> = {
  idle: "bg-ink-500",
  active: "bg-clay-400",
  done: "bg-agent-evaluator",
  error: "bg-red-400",
};

export function AgentNode({ agentId, status, isCurrent, message }: Props) {
  const meta = AGENT_META[agentId];
  const active = status === "active" || isCurrent;

  return (
    <div
      className={[
        "w-[168px] rounded-xl border bg-ink-700/80 backdrop-blur-sm transition-all duration-300",
        active
          ? "border-clay-500/70 animate-pulseGlow scale-[1.03]"
          : status === "done"
          ? "border-agent-evaluator/40"
          : status === "error"
          ? "border-red-500/50"
          : "border-white/8 opacity-70",
      ].join(" ")}
    >
      <div
        className="h-1 rounded-t-xl"
        style={{ backgroundColor: meta.color, opacity: active ? 1 : 0.5 }}
      />
      <div className="p-2.5">
        <div className="flex items-center justify-between">
          <span
            className="text-[10px] font-mono font-bold tracking-wider"
            style={{ color: meta.color }}
          >
            {meta.short}
          </span>
          <span
            className={`h-2 w-2 rounded-full ${STATUS_DOT[status]} ${
              active ? "animate-pulse" : ""
            }`}
          />
        </div>
        <div className="mt-0.5 text-[13px] font-semibold text-stone-100">
          {meta.label}
        </div>
        <div className="text-[10px] leading-tight text-stone-400">
          {meta.blurb}
        </div>
        {active && message && (
          <div className="mt-1.5 line-clamp-2 animate-fadeIn text-[10px] leading-snug text-clay-300">
            {message}
          </div>
        )}
      </div>
    </div>
  );
}
