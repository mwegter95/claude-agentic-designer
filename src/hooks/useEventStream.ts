import { useEffect, useRef } from "react";
import { API_BASE } from "../config";
import { useStore } from "../store/useStore";
import type { AgentEvent } from "../types";

// Subscribes to the backend SSE stream (all runs) and feeds events into the store.
// Reconnects automatically with backoff so the UI survives server restarts.
export function useEventStream() {
  const ingest = useStore((s) => s.ingest);
  const setConnection = useStore((s) => s.setConnection);
  const retryRef = useRef(0);

  useEffect(() => {
    let es: EventSource | null = null;
    let closed = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      setConnection("connecting");
      es = new EventSource(`${API_BASE}/api/events/stream`);

      es.onopen = () => {
        retryRef.current = 0;
        setConnection("open");
      };

      es.onmessage = (e) => {
        try {
          const ev = JSON.parse(e.data) as AgentEvent;
          if (ev && ev.run_id && ev.type) ingest(ev);
        } catch {
          /* ignore keep-alive / non-JSON frames */
        }
      };

      es.onerror = () => {
        setConnection("closed");
        es?.close();
        if (closed) return;
        const delay = Math.min(1000 * 2 ** retryRef.current, 8000);
        retryRef.current += 1;
        timer = setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      es?.close();
    };
  }, [ingest, setConnection]);
}
