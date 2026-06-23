import { api } from "../api/client";
import { useStore } from "../store/useStore";

const STATUS_STYLE: Record<string, string> = {
  running: "bg-clay-600/30 text-clay-300",
  passed: "bg-emerald-500/20 text-emerald-300",
  revise: "bg-amber-500/20 text-amber-300",
  error: "bg-red-500/20 text-red-300",
};

export function RunPanel() {
  const runOrder = useStore((s) => s.runOrder);
  const runs = useStore((s) => s.runs);
  const selectedRunId = useStore((s) => s.selectedRunId);
  const selectRun = useStore((s) => s.selectRun);
  const run = selectedRunId ? runs[selectedRunId] : undefined;

  return (
    <div className="flex h-full flex-col rounded-2xl border border-white/8 bg-ink-800/50">
      <div className="flex items-center gap-2 border-b border-white/8 px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-widest text-stone-400">
          Run
        </span>
        {run && (
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
              STATUS_STYLE[run.status] ?? "bg-ink-600 text-stone-300"
            }`}
          >
            {run.status}
          </span>
        )}
        <select
          value={selectedRunId ?? ""}
          onChange={(e) => selectRun(e.target.value)}
          className="ml-auto max-w-[150px] rounded-md border border-white/10 bg-ink-700 px-2 py-1 text-[11px] text-stone-300 outline-none"
        >
          {runOrder.length === 0 && <option value="">no runs yet</option>}
          {runOrder.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
        {!run ? (
          <div className="space-y-3 text-[11px] text-stone-500">
            <p>No run selected. Start one from Claude, for example:</p>
            <pre className="whitespace-pre-wrap rounded-lg border border-white/8 bg-ink-900/60 p-2 text-[10px] text-stone-400">
{`Make a 6-slide executive deck on our
platform consolidation using the master
brand deck and the example one-pager.`}
            </pre>
            <p>Or smoke-test the UI with the backend simulator:</p>
            <pre className="whitespace-pre-wrap rounded-lg border border-white/8 bg-ink-900/60 p-2 text-[10px] text-stone-400">
{`python tools/simulate_run.py --speed 0.25`}
            </pre>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-2">
              <Stat label="Doc type" value={run.docType ?? "—"} />
              <Stat
                label="Score"
                value={run.score != null ? run.score.toFixed(2) : "—"}
              />
              <Stat label="Iterations" value={String(run.iterations)} />
            </div>

            {run.artifact && (
              <a
                href={api.artifactUrl(run.runId)}
                className="block rounded-lg bg-clay-600/30 py-2 text-center text-[12px] font-semibold text-clay-200 hover:bg-clay-600/40"
              >
                ↓ Download .pptx
              </a>
            )}

            {run.renders.length > 0 && (
              <div className="space-y-1.5">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-stone-500">
                  Slide previews
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {run.renders.map((name) => (
                    <a
                      key={name}
                      href={api.renderUrl(run.runId, name)}
                      target="_blank"
                      rel="noreferrer"
                      className="group overflow-hidden rounded-lg border border-white/10 bg-ink-900"
                    >
                      <img
                        src={api.renderUrl(run.runId, name)}
                        alt={name}
                        className="aspect-video w-full object-cover transition-transform group-hover:scale-105"
                        loading="lazy"
                      />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/8 bg-ink-700/50 p-2 text-center">
      <div className="text-[9px] uppercase tracking-widest text-stone-500">
        {label}
      </div>
      <div className="truncate text-[13px] font-semibold text-stone-100">
        {value}
      </div>
    </div>
  );
}
