import type { AgentId } from "./types";

// In dev, Vite proxies /api to the backend (see vite.config.ts). In a built/
// standalone deployment, override with VITE_API_BASE.
export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export const MAX_LOGS = 3000;

export const AGENT_ORDER: AgentId[] = [
  "orchestrator",
  "design_system",
  "content",
  "structure",
  "layout",
  "builder",
  "reflection",
  "evaluator",
];

export const AGENT_META: Record<
  AgentId,
  { label: string; short: string; color: string; blurb: string }
> = {
  orchestrator: {
    label: "Orchestrator",
    short: "ORC",
    color: "#d97757",
    blurb: "Plans, routes, owns the loop",
  },
  design_system: {
    label: "Design-System",
    short: "DES",
    color: "#e0a872",
    blurb: "Extracts the design contract",
  },
  content: {
    label: "Content",
    short: "CON",
    color: "#8bb4a3",
    blurb: "Audience & key messages",
  },
  structure: {
    label: "Structure",
    short: "STR",
    color: "#7fa8d9",
    blurb: "Doc-type skeleton",
  },
  layout: {
    label: "Layout",
    short: "LAY",
    color: "#9d8bd9",
    blurb: "Maps blocks to master layouts",
  },
  builder: {
    label: "Builder",
    short: "BLD",
    color: "#d98bb4",
    blurb: "Emits plan, builds .pptx",
  },
  reflection: {
    label: "Reflection",
    short: "REF",
    color: "#d9c77f",
    blurb: "Self-critique on renders",
  },
  evaluator: {
    label: "Evaluator",
    short: "EVA",
    color: "#86d99b",
    blurb: "Rubric scoring & gate",
  },
};

// Canvas node coordinates on a 1000x360 viewBox (a left-to-right snake with a
// feedback loop from Evaluator back to Layout).
export const NODE_POS: Record<AgentId, { x: number; y: number }> = {
  orchestrator: { x: 110, y: 90 },
  design_system: { x: 350, y: 90 },
  content: { x: 590, y: 90 },
  structure: { x: 830, y: 90 },
  layout: { x: 830, y: 270 },
  builder: { x: 590, y: 270 },
  reflection: { x: 350, y: 270 },
  evaluator: { x: 110, y: 270 },
};

// Sequential pipeline edges + the dashed feedback/deliver edges.
export const EDGES: { from: AgentId; to: AgentId; kind: "flow" | "loop" }[] = [
  { from: "orchestrator", to: "design_system", kind: "flow" },
  { from: "design_system", to: "content", kind: "flow" },
  { from: "content", to: "structure", kind: "flow" },
  { from: "structure", to: "layout", kind: "flow" },
  { from: "layout", to: "builder", kind: "flow" },
  { from: "builder", to: "reflection", kind: "flow" },
  { from: "reflection", to: "evaluator", kind: "flow" },
  { from: "evaluator", to: "layout", kind: "loop" },
];
