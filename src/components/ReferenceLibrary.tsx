import { useRef, useState } from "react";
import { api } from "../api/client";
import { useStore } from "../store/useStore";
import type { DeviceLogin, ReferenceFile, ReferenceRole } from "../types";

function RoleBadge({ role }: { role: ReferenceRole }) {
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide ${
        role === "master"
          ? "bg-clay-600/30 text-clay-300"
          : "bg-sky-500/20 text-sky-300"
      }`}
    >
      {role}
    </span>
  );
}

function Row({ f, onChange }: { f: ReferenceFile; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  const guard = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      onChange();
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className={`flex items-center gap-2 rounded-lg border px-2.5 py-2 transition-colors ${
        f.enabled
          ? "border-white/10 bg-ink-700/70"
          : "border-white/5 bg-ink-800/40 opacity-55"
      }`}
    >
      <button
        onClick={() => guard(() => api.toggleReference(f.id, !f.enabled))}
        disabled={busy}
        title={f.enabled ? "Referenced this run" : "Not referenced"}
        className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${
          f.enabled ? "bg-clay-500" : "bg-ink-500"
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${
            f.enabled ? "left-[18px]" : "left-0.5"
          }`}
        />
      </button>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <RoleBadge role={f.role} />
          <span className="truncate text-[12px] text-stone-200">{f.name}</span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-stone-500">
          <span>{f.source === "sharepoint" ? "SharePoint" : "Upload"}</span>
          {f.source === "sharepoint" && (
            <span className={f.cached_path ? "text-emerald-400" : "text-amber-400"}>
              {f.cached_path ? "cached" : "not downloaded"}
            </span>
          )}
        </div>
      </div>

      <select
        value={f.role}
        onChange={(e) =>
          guard(() =>
            api.updateReference(f.id, { role: e.target.value as ReferenceRole })
          )
        }
        className="rounded border border-white/10 bg-ink-700 px-1 py-0.5 text-[10px] text-stone-300"
      >
        <option value="master">master</option>
        <option value="example">example</option>
      </select>

      {f.source === "sharepoint" && !f.cached_path && (
        <button
          onClick={() => guard(() => api.downloadSharePoint(f.id))}
          disabled={busy}
          className="rounded bg-ink-600 px-1.5 py-0.5 text-[10px] text-stone-300 hover:bg-ink-500"
        >
          ↓
        </button>
      )}
      <button
        onClick={() => guard(() => api.deleteReference(f.id))}
        disabled={busy}
        className="rounded px-1 text-stone-500 hover:text-red-400"
        title="Remove"
      >
        ✕
      </button>
    </div>
  );
}

function M365SignIn({ onChange }: { onChange: () => void }) {
  const m365 = useStore((s) => s.m365);
  const [device, setDevice] = useState<DeviceLogin | null>(null);
  const [busy, setBusy] = useState(false);

  if (!m365?.configured) return null;
  if (m365.signed_in)
    return (
      <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1.5 text-[11px] text-emerald-300">
        ✓ Signed in to Microsoft 365
      </div>
    );

  return (
    <div className="rounded-lg border border-white/10 bg-ink-700/60 px-2.5 py-2 text-[11px]">
      {!device ? (
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              setDevice(await api.m365Begin());
            } catch (e) {
              alert(String(e));
            } finally {
              setBusy(false);
            }
          }}
          className="w-full rounded bg-clay-600/30 py-1 text-clay-300 hover:bg-clay-600/40"
        >
          Sign in to Microsoft 365
        </button>
      ) : (
        <div className="space-y-1.5">
          <div className="text-stone-300">
            Go to{" "}
            <a
              href={device.verification_uri}
              target="_blank"
              rel="noreferrer"
              className="text-clay-300 underline"
            >
              {device.verification_uri}
            </a>{" "}
            and enter code:
          </div>
          <div className="rounded bg-ink-900 px-2 py-1 text-center font-mono text-base tracking-widest text-clay-300">
            {device.user_code}
          </div>
          <button
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                const r = await api.m365Complete();
                if (!r.signed_in) alert("Not signed in yet — finish in the browser.");
                else setDevice(null);
                onChange();
              } catch (e) {
                alert(String(e));
              } finally {
                setBusy(false);
              }
            }}
            className="w-full rounded bg-ink-600 py-1 text-stone-300 hover:bg-ink-500"
          >
            I've entered the code
          </button>
        </div>
      )}
    </div>
  );
}

export function ReferenceLibrary({ reload }: { reload: () => void }) {
  const references = useStore((s) => s.references);
  const fileInput = useRef<HTMLInputElement>(null);
  const [spUrl, setSpUrl] = useState("");
  const [spRole, setSpRole] = useState<ReferenceRole>("example");
  const [uploadRole, setUploadRole] = useState<ReferenceRole>("master");
  const [busy, setBusy] = useState(false);

  const masters = references.filter((r) => r.role === "master");
  const examples = references.filter((r) => r.role === "example");

  const onUpload = async (file: File) => {
    setBusy(true);
    try {
      await api.uploadReference(file, uploadRole);
      reload();
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(false);
    }
  };

  const onAddSp = async () => {
    if (!spUrl.trim()) return;
    setBusy(true);
    try {
      await api.addSharePoint(spUrl.trim(), "", spRole);
      setSpUrl("");
      reload();
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full flex-col rounded-2xl border border-white/8 bg-ink-800/50">
      <div className="flex items-center gap-2 border-b border-white/8 px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-widest text-stone-400">
          Reference Designs
        </span>
        <span className="rounded-full bg-ink-600 px-2 py-0.5 text-[10px] text-stone-400">
          {references.filter((r) => r.enabled).length} on
        </span>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
        <M365SignIn onChange={reload} />

        {/* Add controls */}
        <div className="space-y-2 rounded-lg border border-white/8 bg-ink-700/40 p-2.5">
          <div className="flex items-center gap-2">
            <select
              value={uploadRole}
              onChange={(e) => setUploadRole(e.target.value as ReferenceRole)}
              className="rounded border border-white/10 bg-ink-700 px-1.5 py-1 text-[10px] text-stone-300"
            >
              <option value="master">master</option>
              <option value="example">example</option>
            </select>
            <input
              ref={fileInput}
              type="file"
              accept=".pptx,.potx,.ppt,.pdf,.png,.jpg,.jpeg"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onUpload(f);
                e.target.value = "";
              }}
            />
            <button
              disabled={busy}
              onClick={() => fileInput.current?.click()}
              className="flex-1 rounded bg-clay-600/30 py-1 text-[11px] text-clay-300 hover:bg-clay-600/40"
            >
              + Upload file
            </button>
          </div>
          <div className="flex items-center gap-1.5">
            <input
              value={spUrl}
              onChange={(e) => setSpUrl(e.target.value)}
              placeholder="SharePoint / OneDrive share URL"
              className="min-w-0 flex-1 rounded border border-white/10 bg-ink-700 px-2 py-1 text-[11px] text-stone-200 outline-none focus:border-clay-500"
            />
            <select
              value={spRole}
              onChange={(e) => setSpRole(e.target.value as ReferenceRole)}
              className="rounded border border-white/10 bg-ink-700 px-1 py-1 text-[10px] text-stone-300"
            >
              <option value="master">master</option>
              <option value="example">example</option>
            </select>
            <button
              disabled={busy}
              onClick={onAddSp}
              className="rounded bg-ink-600 px-2 py-1 text-[11px] text-stone-300 hover:bg-ink-500"
            >
              +
            </button>
          </div>
        </div>

        {/* Lists */}
        {masters.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-stone-500">
              Master deck
            </div>
            {masters.map((f) => (
              <Row key={f.id} f={f} onChange={reload} />
            ))}
          </div>
        )}
        {examples.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-stone-500">
              Examples
            </div>
            {examples.map((f) => (
              <Row key={f.id} f={f} onChange={reload} />
            ))}
          </div>
        )}
        {references.length === 0 && (
          <div className="py-6 text-center text-[11px] text-stone-600">
            Add your master deck and example designs. They persist across runs and
            can be toggled on/off as references.
          </div>
        )}
      </div>
    </div>
  );
}
