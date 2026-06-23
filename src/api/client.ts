import { API_BASE } from "../config";
import type {
  DeviceLogin,
  M365Status,
  ReferenceFile,
  ReferenceRole,
  RunSummary,
} from "../types";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // ── references ────────────────────────────────────────────────────────────
  listReferences: () =>
    http<{ files: ReferenceFile[] }>("/api/references"),

  uploadReference: async (file: File, role: ReferenceRole) => {
    const form = new FormData();
    form.append("file", file);
    form.append("role", role);
    const res = await fetch(`${API_BASE}/api/references/upload`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(await res.text());
    return (await res.json()) as ReferenceFile;
  },

  addSharePoint: (url: string, name: string, role: ReferenceRole) =>
    http<ReferenceFile>("/api/references/sharepoint", {
      method: "POST",
      body: JSON.stringify({ url, name, role }),
    }),

  downloadSharePoint: (id: string) =>
    http<ReferenceFile>(`/api/references/${id}/download`, { method: "POST" }),

  toggleReference: (id: string, enabled: boolean) =>
    http<ReferenceFile>(`/api/references/${id}/toggle`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),

  updateReference: (id: string, patch: { role?: ReferenceRole; name?: string }) =>
    http<ReferenceFile>(`/api/references/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  deleteReference: (id: string) =>
    http<{ ok: boolean }>(`/api/references/${id}`, { method: "DELETE" }),

  // ── runs ──────────────────────────────────────────────────────────────────
  listRuns: () => http<{ runs: RunSummary[] }>("/api/runs"),

  artifactUrl: (runId: string) => `${API_BASE}/api/runs/${runId}/artifact`,
  renderUrl: (runId: string, name: string) =>
    `${API_BASE}/api/runs/${runId}/renders/${name}`,

  // ── microsoft 365 ───────────────────────────────────────────────────────────
  m365Status: () => http<M365Status>("/api/m365/status"),
  m365Begin: () => http<DeviceLogin>("/api/m365/login/begin", { method: "POST" }),
  m365Complete: () =>
    http<{ signed_in: boolean }>("/api/m365/login/complete", { method: "POST" }),

  health: () => http<{ ok: boolean }>("/api/health"),
};
