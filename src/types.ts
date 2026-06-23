export type AgentId =
  | "orchestrator"
  | "design_system"
  | "content"
  | "structure"
  | "layout"
  | "builder"
  | "reflection"
  | "evaluator";

export type EventType =
  | "run_start"
  | "run_end"
  | "agent_start"
  | "agent_thinking"
  | "agent_end"
  | "tool_call"
  | "tool_result"
  | "log"
  | "artifact"
  | "evaluation"
  | "iteration";

export type LogLevel = "debug" | "info" | "warn" | "error";

export interface AgentEvent {
  run_id: string;
  type: EventType;
  seq: number;
  ts: number;
  agent: AgentId | null;
  level: LogLevel;
  message: string;
  data: Record<string, unknown>;
}

export type AgentStatus = "idle" | "active" | "done" | "error";

export interface RunSummary {
  run_id: string;
  created_at: number;
  doc_type?: string;
  status: "running" | "passed" | "revise" | "error";
  score?: number | null;
  iterations: number;
  artifact?: string | null;
  renders: string[];
}

export type ReferenceSource = "upload" | "sharepoint";
export type ReferenceRole = "master" | "example";

export interface ReferenceFile {
  id: string;
  name: string;
  source: ReferenceSource;
  role: ReferenceRole;
  enabled: boolean;
  path?: string | null;
  url?: string | null;
  size?: number | null;
  content_type?: string | null;
  added_at: number;
  cached_path?: string | null;
}

export interface M365Status {
  configured: boolean;
  signed_in: boolean;
}

export interface DeviceLogin {
  verification_uri: string;
  user_code: string;
  message: string;
  expires_in: number;
}
