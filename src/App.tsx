import { useCallback, useEffect } from "react";
import { api } from "./api/client";
import { Header } from "./components/Header";
import { LogsPanel } from "./components/LogsPanel";
import { ReferenceLibrary } from "./components/ReferenceLibrary";
import { RunPanel } from "./components/RunPanel";
import { WorkflowCanvas } from "./components/WorkflowCanvas";
import { useEventStream } from "./hooks/useEventStream";
import { useStore } from "./store/useStore";

export default function App() {
  useEventStream();
  const setReferences = useStore((s) => s.setReferences);
  const setM365 = useStore((s) => s.setM365);

  const reload = useCallback(async () => {
    try {
      const [refs, m365] = await Promise.all([
        api.listReferences(),
        api.m365Status().catch(() => null),
      ]);
      setReferences(refs.files);
      setM365(m365);
    } catch {
      /* server may not be up yet; SSE hook will retry */
    }
  }, [setReferences, setM365]);

  useEffect(() => {
    reload();
    const t = setInterval(reload, 15000);
    return () => clearInterval(t);
  }, [reload]);

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Header />
      <main className="flex min-h-0 flex-1 gap-3 p-3">
        {/* Left: workflow canvas (top) + logs (lower-left) */}
        <section className="flex min-w-0 flex-1 flex-col gap-3">
          <div className="min-h-0 flex-[3]">
            <WorkflowCanvas />
          </div>
          <div className="min-h-0 flex-[2]">
            <LogsPanel />
          </div>
        </section>

        {/* Right: run + reference library */}
        <aside className="flex w-[380px] shrink-0 flex-col gap-3">
          <div className="min-h-0 flex-[2]">
            <RunPanel />
          </div>
          <div className="min-h-0 flex-[3]">
            <ReferenceLibrary reload={reload} />
          </div>
        </aside>
      </main>
    </div>
  );
}
