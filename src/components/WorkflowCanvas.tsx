import { useStore } from "../store/useStore";
import { AGENT_ORDER, EDGES, NODE_POS } from "../config";
import type { AgentId } from "../types";
import { AgentNode } from "./AgentNode";

const VW = 1000;
const VH = 360;

function center(a: AgentId) {
  return NODE_POS[a];
}

function flowPath(from: AgentId, to: AgentId) {
  const a = center(from);
  const b = center(to);
  const mx = (a.x + b.x) / 2;
  // gentle S-curve between adjacent nodes
  return `M ${a.x} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`;
}

function loopPath(from: AgentId, to: AgentId) {
  const a = center(from); // evaluator (bottom-left)
  const b = center(to); // layout (bottom-right)
  // arc that dips below the bottom row to read as a feedback loop
  return `M ${a.x} ${a.y + 30} C ${VW * 0.3} ${VH + 30}, ${VW * 0.7} ${
    VH + 30
  }, ${b.x} ${b.y + 30}`;
}

export function WorkflowCanvas() {
  const selectedRunId = useStore((s) => s.selectedRunId);
  const run = useStore((s) => (selectedRunId ? s.runs[selectedRunId] : undefined));

  const agentStatus = run?.agentStatus;
  const current = run?.currentAgent ?? null;

  const isEdgeActive = (to: AgentId) => current === to;
  const isEdgeDone = (from: AgentId, to: AgentId) =>
    agentStatus?.[from] === "done" && agentStatus?.[to] === "done";

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl border border-white/8 bg-ink-800/40 p-3">
      <div className="pointer-events-none absolute left-4 top-3 z-10 flex items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-widest text-stone-400">
          Workflow
        </span>
        {run && (
          <span className="rounded-full bg-ink-600 px-2 py-0.5 text-[10px] text-stone-300">
            {run.docType ?? "—"} · iter {run.iterations}
          </span>
        )}
      </div>

      <div className="relative h-full w-full">
        <svg
          viewBox={`0 0 ${VW} ${VH + 40}`}
          preserveAspectRatio="xMidYMid meet"
          className="absolute inset-0 h-full w-full"
        >
          <defs>
            <marker
              id="arrow"
              markerWidth="8"
              markerHeight="8"
              refX="6"
              refY="3"
              orient="auto"
            >
              <path d="M0,0 L6,3 L0,6 Z" fill="#6b6051" />
            </marker>
            <marker
              id="arrow-active"
              markerWidth="9"
              markerHeight="9"
              refX="6"
              refY="3"
              orient="auto"
            >
              <path d="M0,0 L6,3 L0,6 Z" fill="#d97757" />
            </marker>
          </defs>

          {EDGES.map((e, i) => {
            const active = e.kind === "flow" && isEdgeActive(e.to);
            const done = isEdgeDone(e.from, e.to);
            const d = e.kind === "loop" ? loopPath(e.from, e.to) : flowPath(e.from, e.to);
            const stroke = active ? "#d97757" : done ? "#7a6e5c" : "#3a332a";
            return (
              <path
                key={i}
                d={d}
                fill="none"
                stroke={stroke}
                strokeWidth={active ? 2.5 : 1.5}
                strokeDasharray={e.kind === "loop" ? "6 6" : active ? "8 8" : undefined}
                className={active ? "animate-dash" : ""}
                markerEnd={active ? "url(#arrow-active)" : "url(#arrow)"}
                opacity={e.kind === "loop" ? 0.65 : 1}
              />
            );
          })}
          <text
            x={VW / 2}
            y={VH + 34}
            textAnchor="middle"
            fontSize="11"
            fill="#6b6051"
          >
            revise loop (max 3 iterations)
          </text>
        </svg>

        {AGENT_ORDER.map((a) => {
          const pos = NODE_POS[a];
          return (
            <div
              key={a}
              className="absolute -translate-x-1/2 -translate-y-1/2"
              style={{
                left: `${(pos.x / VW) * 100}%`,
                top: `${(pos.y / (VH + 40)) * 100}%`,
              }}
            >
              <AgentNode
                agentId={a}
                status={agentStatus?.[a] ?? "idle"}
                isCurrent={current === a}
                message={run?.lastMessage?.[a]}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
