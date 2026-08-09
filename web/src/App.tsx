import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertOctagon,
  Archive,
  CalendarClock,
  Check,
  ClipboardList,
  Database,
  FileUp,
  Gauge,
  Inbox,
  LayoutDashboard,
  LogOut,
  Megaphone,
  MessageSquare,
  Plus,
  RefreshCw,
  Send,
  ShieldCheck,
  UserRoundX,
  Users,
  X,
} from "lucide-react";
import { api, JsonRecord } from "./api";

type ViewName = "dashboard" | "intake" | "campaigns" | "messages" | "responses" | "followups" | "privacy" | "operations";
type StatusData = {
  runtime: { live_search_enabled?: boolean; live_send_enabled?: boolean; provider_authorization?: { ready?: boolean } };
  database: { ready?: boolean; integrity?: string; schema_version?: number };
  safety_stop_active: boolean;
  hai_feed: { available: boolean; mode: string };
  timestamp: string;
};
type ItemEnvelope = { items: JsonRecord[] };

const navigation: Array<{ key: ViewName; label: string; icon: typeof Gauge }> = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "intake", label: "Candidate Intake", icon: Users },
  { key: "campaigns", label: "Campaigns", icon: Megaphone },
  { key: "messages", label: "Messages", icon: Inbox },
  { key: "responses", label: "Responses", icon: MessageSquare },
  { key: "followups", label: "Follow-ups", icon: CalendarClock },
  { key: "privacy", label: "Privacy", icon: ShieldCheck },
  { key: "operations", label: "Operations", icon: Gauge },
];

function value(item: JsonRecord, key: string, fallback = "-"): string {
  const raw = item[key];
  return raw === null || raw === undefined || raw === "" ? fallback : String(raw);
}

function StatusDot({ tone = "good" }: { tone?: "good" | "warn" | "bad" | "info" }) {
  return <span className={`status-dot ${tone}`} aria-hidden="true" />;
}

function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>;
}

function Section({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return <section className="section"><div className="section-heading"><h2>{title}</h2>{action}</div>{children}</section>;
}

function Result({ text, error = false }: { text: string; error?: boolean }) {
  return text ? <p className={error ? "form-error" : "result-text"} role={error ? "alert" : "status"}>{text}</p> : null;
}

function CompactTable({ rows, columns, onSelect, selectedId }: { rows: JsonRecord[]; columns: string[]; onSelect?: (row: JsonRecord) => void; selectedId?: unknown }) {
  return <div className="table-wrap"><table><thead><tr>{columns.map((column) => <th key={column}>{column.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={value(row, "id", value(row, "volunteer_id", String(index)))} className={`${onSelect ? "selectable" : ""} ${selectedId === row.id || selectedId === row.volunteer_id ? "selected" : ""}`} onClick={() => onSelect?.(row)} tabIndex={onSelect ? 0 : undefined} onKeyDown={(event) => { if (onSelect && (event.key === "Enter" || event.key === " ")) onSelect(row); }}>{columns.map((column) => <td key={column}>{value(row, column)}</td>)}</tr>)}</tbody></table></div>;
}

function Login({ onConnect }: { onConnect: (token: string) => Promise<void> }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { await onConnect(token.trim()); } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not connect"); }
    finally { setBusy(false); }
  }
  return <main className="login-shell"><form className="login-panel" onSubmit={submit}><div className="brand"><strong><span>NL</span>voorelkaar</strong><small>Reachout</small></div><h1>Operator access</h1><label>Access token<input type="password" autoComplete="current-password" value={token} onChange={(event) => setToken(event.target.value)} minLength={32} required autoFocus /></label><Result text={error} error /><button className="primary" disabled={busy || token.trim().length < 32}>{busy ? "Connecting..." : "Connect"}</button></form></main>;
}

function Readiness({ status }: { status: StatusData }) {
  const providerReady = Boolean(status.runtime.provider_authorization?.ready);
  const rows = [
    ["Local assistance", "Active", "Operator-controlled workflow", "good"],
    ["Provider automation", providerReady ? "Authorized" : "Disabled", providerReady ? "Written approval current" : "Written platform approval required", providerReady ? "good" : "warn"],
    ["Database", status.database.ready ? "Healthy" : "Needs attention", status.database.integrity ?? "Unknown", status.database.ready ? "good" : "bad"],
    ["HAI feed", status.hai_feed.available ? "Available" : "Unavailable", "Read-only, privacy-minimized", status.hai_feed.available ? "good" : "bad"],
    ["Safety stop", status.safety_stop_active ? "ACTIVE" : "Clear", status.safety_stop_active ? "Manual completion blocked" : "No emergency stop", status.safety_stop_active ? "bad" : "good"],
  ];
  return <div className="readiness-list">{rows.map(([name, state, detail, tone]) => <div className="readiness-row" key={name}><strong>{name}</strong><span><StatusDot tone={tone as "good" | "warn" | "bad"} />{state}</span><span>{detail}</span></div>)}</div>;
}

function DashboardView({ token, status, refreshStatus }: { token: string; status: StatusData; refreshStatus: () => void }) {
  const [data, setData] = useState<JsonRecord | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => { setError(""); try { setData(await api<JsonRecord>("/api/v1/dashboard", token)); } catch (reason) { setError(reason instanceof Error ? reason.message : "Load failed"); } }, [token]);
  useEffect(() => { void load(); }, [load]);
  const campaigns = (data?.campaigns as JsonRecord[] | undefined) ?? [];
  const reviews = (data?.review_queue as JsonRecord[] | undefined) ?? [];
  const responses = (data?.responses as JsonRecord[] | undefined) ?? [];
  return <><div className="status-strip"><div><Database /><span>Database</span><strong>{status.database.ready ? "Healthy" : "Attention"}</strong></div><div><ShieldCheck /><span>Provider approval</span><strong>{status.runtime.provider_authorization?.ready ? "Current" : "Required"}</strong></div><div><ClipboardList /><span>HAI feed</span><strong>{status.hai_feed.available ? "Available" : "Unavailable"}</strong></div><button className="icon-button" title="Refresh status" aria-label="Refresh status" onClick={() => { refreshStatus(); void load(); }}><RefreshCw /></button></div><Result text={error} error /><div className="dashboard-grid"><Section title="Operational readiness"><Readiness status={status} /></Section><Section title="Campaign pipeline">{campaigns.length ? <CompactTable rows={campaigns} columns={["name", "status", "target_location", "updated_at"]} /> : <EmptyState>No campaigns yet.</EmptyState>}</Section></div><Section title="Messages in review">{reviews.length ? <CompactTable rows={reviews} columns={["id", "campaign_name", "status", "updated_at"]} /> : <EmptyState>No messages require review.</EmptyState>}</Section><Section title="Recent responses">{responses.length ? <CompactTable rows={responses} columns={["id", "campaign_name", "received_at", "status"]} /> : <EmptyState>No responses have been recorded.</EmptyState>}</Section></>;
}

function IntakeView({ token }: { token: string }) {
  const [file, setFile] = useState<File | null>(null); const [items, setItems] = useState<JsonRecord[]>([]); const [result, setResult] = useState(""); const [error, setError] = useState(false); const [busy, setBusy] = useState(false);
  const load = useCallback(async () => setItems((await api<ItemEnvelope>("/api/v1/volunteers?limit=100", token)).items), [token]);
  useEffect(() => { void load(); }, [load]);
  async function submit(event: FormEvent) { event.preventDefault(); if (!file) return; setBusy(true); setError(false); const form = new FormData(); form.append("file", file); try { const data = await api<JsonRecord>("/api/v1/volunteers/import", token, { method: "POST", body: form }); setResult(`Imported ${data.imported ?? 0}, updated ${data.updated ?? 0}, skipped ${data.skipped ?? 0}.`); await load(); } catch (reason) { setError(true); setResult(reason instanceof Error ? reason.message : "Import failed"); } finally { setBusy(false); } }
  return <><Section title="Candidate intake"><form className="inline-form" onSubmit={submit}><label>Reviewed CSV or JSON<input type="file" accept=".csv,.json,application/json,text/csv" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required /></label><button className="primary" disabled={busy || !file}><FileUp />{busy ? "Importing..." : "Import"}</button></form><Result text={result} error={error} /></Section><Section title="Imported candidates">{items.length ? <CompactTable rows={items} columns={["volunteer_id", "name", "location", "categories", "retention_status"]} /> : <EmptyState>No candidates have been imported.</EmptyState>}</Section></>;
}

function CampaignsView({ token }: { token: string }) {
  const [items, setItems] = useState<JsonRecord[]>([]); const [selected, setSelected] = useState<JsonRecord | null>(null); const [message, setMessage] = useState(""); const [error, setError] = useState(false);
  const load = useCallback(async () => { const rows = (await api<ItemEnvelope>("/api/v1/campaigns", token)).items; setItems(rows); setSelected((current) => current ? rows.find((row) => row.id === current.id) ?? null : null); }, [token]);
  useEffect(() => { void load(); }, [load]);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); const body = { name: data.get("name"), target_location: data.get("location"), target_categories: data.get("categories"), description: data.get("description"), message_template: data.get("template") }; try { const created = await api<JsonRecord>("/api/v1/campaigns", token, { method: "POST", body: JSON.stringify(body) }); form.reset(); setError(false); setMessage(`Campaign #${created.id} created.`); await load(); } catch (reason) { setError(true); setMessage(reason instanceof Error ? reason.message : "Could not create campaign"); } }
  async function createDrafts() { if (!selected) return; try { const result = await api<{ ids: number[] }>(`/api/v1/campaigns/${selected.id}/drafts`, token, { method: "POST", body: JSON.stringify({ volunteer_ids: null }) }); setError(false); setMessage(`${result.ids.length} draft(s) created for ${value(selected, "name")}.`); } catch (reason) { setError(true); setMessage(reason instanceof Error ? reason.message : "Draft creation failed"); } }
  return <div className="split-view"><Section title="Campaigns" action={<button className="secondary" disabled={!selected} onClick={() => void createDrafts()}><ClipboardList />Create drafts</button>}>{items.length ? <CompactTable rows={items} columns={["id", "name", "status", "target_location", "updated_at"]} onSelect={setSelected} selectedId={selected?.id} /> : <EmptyState>No campaigns yet.</EmptyState>}<Result text={message} error={error} /></Section><Section title="Create campaign"><form className="stack-form" onSubmit={submit}><label>Name<input name="name" required maxLength={200} /></label><label>Location<input name="location" maxLength={200} /></label><label>Categories<input name="categories" maxLength={500} /></label><label>Description<textarea name="description" rows={3} maxLength={2000} /></label><label>Message template<textarea name="template" rows={7} required maxLength={20000} /></label><button className="primary"><Plus />Create</button></form></Section></div>;
}

function MessagesView({ token }: { token: string }) {
  const [mode, setMode] = useState<"draft" | "approved">("draft"); const [items, setItems] = useState<JsonRecord[]>([]); const [selected, setSelected] = useState<JsonRecord | null>(null); const [note, setNote] = useState(""); const [message, setMessage] = useState(""); const [error, setError] = useState(false);
  const load = useCallback(async () => { const endpoint = mode === "draft" ? "/api/v1/messages/review" : "/api/v1/messages?message_status=approved"; const rows = (await api<ItemEnvelope>(endpoint, token)).items; setItems(rows); setSelected((current) => current ? rows.find((row) => row.id === current.id) ?? rows[0] ?? null : rows[0] ?? null); }, [mode, token]);
  useEffect(() => { void load(); }, [load]);
  async function act(action: "approve" | "reject" | "confirm-manual-send") { if (!selected || !note.trim()) return; const body = action === "confirm-manual-send" ? { evidence: note } : { reason: note }; try { await api(`/api/v1/messages/${selected.id}/${action}`, token, { method: "POST", body: JSON.stringify(body) }); setNote(""); setError(false); setMessage(action === "approve" ? "Draft approved." : action === "reject" ? "Draft rejected." : "Manual send recorded with evidence."); await load(); } catch (reason) { setError(true); setMessage(reason instanceof Error ? reason.message : "Operation failed"); } }
  return <div className="split-view wide-detail"><Section title="Message queue" action={<div className="segmented" aria-label="Message queue"><button className={mode === "draft" ? "active" : ""} onClick={() => setMode("draft")}>Review</button><button className={mode === "approved" ? "active" : ""} onClick={() => setMode("approved")}>Approved</button></div>}>{items.length ? <CompactTable rows={items} columns={["id", "campaign_name", "volunteer_name", "status"]} onSelect={setSelected} selectedId={selected?.id} /> : <EmptyState>{mode === "draft" ? "No messages require review." : "No approved messages await manual completion."}</EmptyState>}</Section><Section title={selected ? `Draft #${selected.id}` : "Draft detail"}>{selected ? <div className="review-detail"><h3>{value(selected, "subject", "No subject")}</h3><pre>{value(selected, "body", "No message body")}</pre><label>{mode === "draft" ? "Decision reason" : "Manual delivery evidence"}<textarea rows={4} value={note} onChange={(event) => setNote(event.target.value)} maxLength={4000} /></label><div className="button-row">{mode === "draft" ? <><button className="primary" onClick={() => void act("approve")} disabled={!note.trim()}><Check />Approve</button><button className="danger" onClick={() => void act("reject")} disabled={!note.trim()}><X />Reject</button></> : <button className="primary" onClick={() => void act("confirm-manual-send")} disabled={note.trim().length < 3}><Send />Record manual send</button>}</div><Result text={message} error={error} /></div> : <EmptyState>Select a message.</EmptyState>}</Section></div>;
}

function ResponsesView({ token }: { token: string }) {
  const [items, setItems] = useState<JsonRecord[]>([]); const [message, setMessage] = useState(""); const [error, setError] = useState(false);
  const load = useCallback(async () => setItems((await api<ItemEnvelope>("/api/v1/responses", token)).items), [token]);
  useEffect(() => { void load(); }, [load]);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); try { await api("/api/v1/responses", token, { method: "POST", body: JSON.stringify({ volunteer_id: data.get("volunteer_id"), campaign_id: Number(data.get("campaign_id")), content: data.get("content") }) }); form.reset(); setError(false); setMessage("Response recorded for operator review."); await load(); } catch (reason) { setError(true); setMessage(reason instanceof Error ? reason.message : "Response could not be recorded"); } }
  return <div className="split-view"><Section title="Responses">{items.length ? <CompactTable rows={items} columns={["id", "campaign_name", "volunteer_name", "received_at", "classification"]} /> : <EmptyState>No responses have been recorded.</EmptyState>}</Section><Section title="Record response"><form className="stack-form" onSubmit={submit}><label>Volunteer ID<input name="volunteer_id" required maxLength={200} /></label><label>Campaign ID<input name="campaign_id" type="number" min="1" required /></label><label>Response content<textarea name="content" rows={8} required maxLength={200000} /></label><button className="primary"><Plus />Record</button></form><Result text={message} error={error} /></Section></div>;
}

function FollowUpsView({ token }: { token: string }) {
  const [items, setItems] = useState<JsonRecord[]>([]); const [selected, setSelected] = useState<JsonRecord | null>(null); const [evidence, setEvidence] = useState(""); const [message, setMessage] = useState(""); const [error, setError] = useState(false);
  const load = useCallback(async () => { const rows = (await api<ItemEnvelope>("/api/v1/follow-ups", token)).items; setItems(rows); setSelected((current) => current ? rows.find((row) => row.id === current.id) ?? null : rows[0] ?? null); }, [token]);
  useEffect(() => { void load(); }, [load]);
  async function act(action: "approve" | "confirm-manual-send") { if (!selected || (action === "confirm-manual-send" && evidence.trim().length < 3)) return; try { await api(`/api/v1/follow-ups/${selected.id}/${action}`, token, { method: "POST", body: action === "approve" ? undefined : JSON.stringify({ evidence }) }); setEvidence(""); setError(false); setMessage(action === "approve" ? "Follow-up approved." : "Follow-up send recorded with evidence."); await load(); } catch (reason) { setError(true); setMessage(reason instanceof Error ? reason.message : "Operation failed"); } }
  const status = selected ? value(selected, "status") : "";
  return <div className="split-view wide-detail"><Section title="Follow-up queue">{items.length ? <CompactTable rows={items} columns={["id", "campaign_name", "volunteer_name", "status", "due_at"]} onSelect={setSelected} selectedId={selected?.id} /> : <EmptyState>No follow-ups are queued.</EmptyState>}</Section><Section title={selected ? `Follow-up #${selected.id}` : "Follow-up detail"}>{selected ? <div className="review-detail"><h3>{value(selected, "campaign_name", "Follow-up")}</h3><pre>{value(selected, status === "approved" ? "approved_message_snapshot" : "suggested_message", "No suggested message")}</pre>{status === "approved" && <label>Manual delivery evidence<textarea rows={4} value={evidence} onChange={(event) => setEvidence(event.target.value)} maxLength={4000} /></label>}<div className="button-row">{status === "due" && <button className="primary" onClick={() => void act("approve")}><Check />Approve follow-up</button>}{status === "approved" && <button className="primary" disabled={evidence.trim().length < 3} onClick={() => void act("confirm-manual-send")}><Send />Record manual send</button>}</div><Result text={message} error={error} /></div> : <EmptyState>Select a follow-up.</EmptyState>}</Section></div>;
}

function PrivacyView({ token }: { token: string }) {
  const [items, setItems] = useState<JsonRecord[]>([]); const [selected, setSelected] = useState<JsonRecord | null>(null); const [reason, setReason] = useState(""); const [message, setMessage] = useState(""); const [error, setError] = useState(false);
  const load = useCallback(async () => { const rows = (await api<ItemEnvelope>("/api/v1/privacy/retention", token)).items; setItems(rows); setSelected((current) => current ? rows.find((row) => row.volunteer_id === current.volunteer_id) ?? null : rows[0] ?? null); }, [token]);
  useEffect(() => { void load(); }, [load]);
  async function act(action: "archive" | "redact") { if (!selected || !reason.trim()) return; try { await api(`/api/v1/privacy/retention/${encodeURIComponent(value(selected, "volunteer_id"))}/${action}`, token, { method: "POST", body: JSON.stringify({ reason }) }); setReason(""); setError(false); setMessage(action === "archive" ? "Volunteer archived." : "Personal profile data redacted."); await load(); } catch (cause) { setError(true); setMessage(cause instanceof Error ? cause.message : "Privacy action failed"); } }
  return <div className="split-view wide-detail"><Section title="Privacy retention review">{items.length ? <CompactTable rows={items} columns={["volunteer_id", "name", "updated_at", "contact_count", "response_count"]} onSelect={setSelected} selectedId={selected?.volunteer_id} /> : <EmptyState>No records currently meet the retention threshold.</EmptyState>}</Section><Section title={selected ? `Review ${value(selected, "volunteer_id")}` : "Retention decision"}>{selected ? <div className="review-detail"><dl className="detail-list"><div><dt>Name</dt><dd>{value(selected, "name")}</dd></div><div><dt>Last updated</dt><dd>{value(selected, "updated_at")}</dd></div><div><dt>Contacts</dt><dd>{value(selected, "contact_count", "0")}</dd></div><div><dt>Responses</dt><dd>{value(selected, "response_count", "0")}</dd></div></dl><label>Decision reason<textarea rows={4} value={reason} onChange={(event) => setReason(event.target.value)} maxLength={2000} /></label><div className="button-row"><button className="secondary" disabled={!reason.trim()} onClick={() => void act("archive")}><Archive />Archive</button><button className="danger" disabled={!reason.trim()} onClick={() => void act("redact")}><UserRoundX />Redact personal data</button></div><Result text={message} error={error} /></div> : <EmptyState>Select a retention candidate.</EmptyState>}</Section></div>;
}

function OperationsView({ token, status, refreshStatus }: { token: string; status: StatusData; refreshStatus: () => void }) {
  const [message, setMessage] = useState(""); const [error, setError] = useState(false);
  async function setStop(active: boolean) { try { await api("/api/v1/operations/safety-stop", token, { method: "PUT", body: JSON.stringify({ active }) }); setError(false); setMessage(active ? "Safety stop activated." : "Safety stop cleared."); refreshStatus(); } catch (reason) { setError(true); setMessage(reason instanceof Error ? reason.message : "Operation failed"); } }
  return <div className="operations-layout"><Section title="Operations and safety"><Readiness status={status} /><div className="button-row operations-actions">{status.safety_stop_active ? <button className="secondary" onClick={() => void setStop(false)}><Check />Clear safety stop</button> : <button className="danger solid" onClick={() => void setStop(true)}><AlertOctagon />Activate safety stop</button>}</div><Result text={message} error={error} /></Section><Section title="Integration state"><dl className="detail-list"><div><dt>HAI connector</dt><dd>{status.hai_feed.available ? "Read-only feed available" : "Unavailable"}</dd></div><div><dt>Database schema</dt><dd>{status.database.schema_version ?? "Unknown"}</dd></div><div><dt>Provider search</dt><dd>{status.runtime.live_search_enabled ? "Enabled" : "Disabled"}</dd></div><div><dt>Provider send</dt><dd>{status.runtime.live_send_enabled ? "Enabled" : "Disabled"}</dd></div></dl></Section></div>;
}

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem("nlve-token") ?? ""); const [status, setStatus] = useState<StatusData | null>(null); const [view, setView] = useState<ViewName>("dashboard"); const [connectionError, setConnectionError] = useState("");
  const connect = useCallback(async (candidate: string) => { const nextStatus = await api<StatusData>("/api/v1/status", candidate); sessionStorage.setItem("nlve-token", candidate); setToken(candidate); setStatus(nextStatus); }, []);
  const refreshStatus = useCallback(() => { if (!token) return; setConnectionError(""); void api<StatusData>("/api/v1/status", token).then(setStatus).catch((reason) => setConnectionError(reason instanceof Error ? reason.message : "Connection lost")); }, [token]);
  useEffect(() => { if (token && !status) void connect(token).catch(() => { sessionStorage.removeItem("nlve-token"); setToken(""); }); }, [connect, status, token]);
  const title = useMemo(() => navigation.find((item) => item.key === view)?.label ?? "Dashboard", [view]);
  if (!token || !status) return <Login onConnect={connect} />;
  const views: Record<ViewName, ReactNode> = { dashboard: <DashboardView token={token} status={status} refreshStatus={refreshStatus} />, intake: <IntakeView token={token} />, campaigns: <CampaignsView token={token} />, messages: <MessagesView token={token} />, responses: <ResponsesView token={token} />, followups: <FollowUpsView token={token} />, privacy: <PrivacyView token={token} />, operations: <OperationsView token={token} status={status} refreshStatus={refreshStatus} /> };
  return <div className="app-shell"><aside><div className="brand"><strong><span>NL</span>voorelkaar</strong><small>Reachout</small></div><nav aria-label="Primary navigation">{navigation.map(({ key, label, icon: Icon }) => <button key={key} title={label} className={view === key ? "active" : ""} onClick={() => setView(key)}><Icon />{label}</button>)}</nav><button className="logout" onClick={() => { sessionStorage.removeItem("nlve-token"); setToken(""); setStatus(null); }}><LogOut />Disconnect</button></aside><main><header><div><span className="mode"><StatusDot tone={status.safety_stop_active ? "bad" : "good"} />{status.safety_stop_active ? "Safety stop active" : "Local assistance active"}</span><h1>{title}</h1></div><button className="icon-button" title="Refresh" aria-label="Refresh current status" onClick={refreshStatus}><RefreshCw /></button></header><Result text={connectionError} error /><div className="content">{views[view]}</div></main></div>;
}
