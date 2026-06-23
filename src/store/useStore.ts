import { create } from "zustand";
import { AGENT_ORDER, MAX_LOGS } from "../config";
import type {
  AgentEvent,
  AgentId,
  AgentStatus,
  M365Status,
  ReferenceFile,
} from "../types";

export interface RunState {
  runId: string;
  createdAt: number;
  docType?: string;
  status: "running" | "passed" | "revise" | "error";
  score?: number | null;
  iterations: number;
  artifact?: string | null;
  renders: string[];
  events: AgentEvent[];
  agentStatus: Record<AgentId, AgentStatus>;
  currentAgent: AgentId | null;
  lastMessage: Partial<Record<AgentId, string>>;
}

interface DesignerStore {
  connection: "connecting" | "open" | "closed";
  runs: Record<string, RunState>;
  runOrder: string[];
  selectedRunId: string | null;
  autoFollow: boolean;
  references: ReferenceFile[];
  m365: M365Status | null;

  setConnection: (c: DesignerStore["connection"]) => void;
  ingest: (ev: AgentEvent) => void;
  selectRun: (id: string) => void;
  setReferences: (r: ReferenceFile[]) => void;
  setM365: (m: M365Status | null) => void;
  clearRun: (id: string) => void;
}

function emptyAgentStatus(): Record<AgentId, AgentStatus> {
  return AGENT_ORDER.reduce(
    (acc, a) => ((acc[a] = "idle"), acc),
    {} as Record<AgentId, AgentStatus>
  );
}

function newRun(ev: AgentEvent): RunState {
  return {
    runId: ev.run_id,
    createdAt: ev.ts,
    status: "running",
    iterations: 0,
    renders: [],
    events: [],
    agentStatus: emptyAgentStatus(),
    currentAgent: null,
    lastMessage: {},
  };
}

function applyEvent(run: RunState, ev: AgentEvent): RunState {
  const events = [...run.events, ev];
  if (events.length > MAX_LOGS) events.splice(0, events.length - MAX_LOGS);

  const agentStatus = { ...run.agentStatus };
  const lastMessage = { ...run.lastMessage };
  let currentAgent = run.currentAgent;
  let status = run.status;
  let score = run.score;
  let iterations = run.iterations;
  let artifact = run.artifact;
  let renders = run.renders;
  let docType = run.docType;

  if (ev.agent) lastMessage[ev.agent] = ev.message;

  switch (ev.type) {
    case "run_start":
      docType = (ev.data?.doc_type as string) ?? docType;
      status = "running";
      break;
    case "agent_start":
      if (ev.agent) {
        agentStatus[ev.agent] = "active";
        currentAgent = ev.agent;
      }
      break;
    case "agent_end":
      if (ev.agent) agentStatus[ev.agent] = "done";
      break;
    case "agent_thinking":
    case "tool_call":
    case "tool_result":
      if (ev.agent) {
        if (agentStatus[ev.agent] !== "done") agentStatus[ev.agent] = "active";
        currentAgent = ev.agent;
      }
      break;
    case "iteration":
      iterations += 1;
      // Re-arm the downstream agents for another pass.
      ["layout", "builder", "reflection", "evaluator"].forEach((a) => {
        agentStatus[a as AgentId] = "idle";
      });
      break;
    case "evaluation":
      score = (ev.data?.weighted_score as number) ?? score;
      status = (ev.data?.passed as boolean) ? "passed" : "revise";
      break;
    case "artifact":
      if (ev.data?.kind === "pptx" && ev.data?.out)
        artifact = String(ev.data.out);
      if (Array.isArray(ev.data?.renders))
        renders = (ev.data.renders as string[]).map(String);
      break;
    case "run_end":
      status = ((ev.data?.status as RunState["status"]) ?? "passed");
      if (typeof ev.data?.score === "number") score = ev.data.score as number;
      if (currentAgent) agentStatus[currentAgent] = "done";
      currentAgent = null;
      break;
    case "log":
      if (ev.level === "error" && ev.agent) agentStatus[ev.agent] = "error";
      break;
  }

  return {
    ...run,
    events,
    agentStatus,
    lastMessage,
    currentAgent,
    status,
    score,
    iterations,
    artifact,
    renders,
    docType,
  };
}

export const useStore = create<DesignerStore>((set) => ({
  connection: "connecting",
  runs: {},
  runOrder: [],
  selectedRunId: null,
  autoFollow: true,
  references: [],
  m365: null,

  setConnection: (c) => set({ connection: c }),

  ingest: (ev) =>
    set((state) => {
      const existing = state.runs[ev.run_id] ?? newRun(ev);
      const updated = applyEvent(existing, ev);
      const runs = { ...state.runs, [ev.run_id]: updated };
      let runOrder = state.runOrder;
      if (!state.runOrder.includes(ev.run_id)) {
        runOrder = [ev.run_id, ...state.runOrder];
      }
      let selectedRunId = state.selectedRunId;
      if (
        selectedRunId === null ||
        (state.autoFollow && ev.type === "run_start")
      ) {
        selectedRunId = ev.run_id;
      }
      return { runs, runOrder, selectedRunId };
    }),

  selectRun: (id) => set({ selectedRunId: id, autoFollow: false }),

  setReferences: (references) => set({ references }),
  setM365: (m365) => set({ m365 }),

  clearRun: (id) =>
    set((state) => {
      const runs = { ...state.runs };
      delete runs[id];
      const runOrder = state.runOrder.filter((r) => r !== id);
      const selectedRunId =
        state.selectedRunId === id ? runOrder[0] ?? null : state.selectedRunId;
      return { runs, runOrder, selectedRunId };
    }),
}));
