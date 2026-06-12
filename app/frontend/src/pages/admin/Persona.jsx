import React, { useCallback, useEffect, useState } from "react";
import { Compass } from "lucide-react";
import { api } from "../../lib/api";
import useApiAction from "../../lib/hooks/useApiAction";
import PersonaOverviewCards from "../../features/admin/persona/PersonaOverviewCards";
import PersonaQuestionBankTable from "../../features/admin/persona/PersonaQuestionBankTable";
import PersonaQuestionEditor from "../../features/admin/persona/PersonaQuestionEditor";
import PersonaSnapshotTable from "../../features/admin/persona/PersonaSnapshotTable";
import PersonaUserInspector from "../../features/admin/persona/PersonaUserInspector";
import PersonaQueueTable from "../../features/admin/persona/PersonaQueueTable";
import PersonaSignalEventsTable from "../../features/admin/persona/PersonaSignalEventsTable";
import { AdminSafetyBanner } from "../../shared/ui/core";
import { PageHeader, StatusDot } from "../../shared/ui/studyos";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "questions", label: "Question Bank" },
  { id: "snapshots", label: "Snapshots" },
  { id: "inspector", label: "User Inspector" },
  { id: "queue", label: "Recompute Queue" },
  { id: "events", label: "Signal Events" },
];

export default function AdminPersona() {
  const [tab, setTab] = useState("overview");
  const [overview, setOverview] = useState(null);
  const [overviewError, setOverviewError] = useState("");

  // Question bank state
  const [bank, setBank] = useState({ items: [], count: 0 });
  const [bankActiveFilter, setBankActiveFilter] = useState("all");
  const [bankQuery, setBankQuery] = useState("");
  const [bankLoading, setBankLoading] = useState(false);
  const [bankError, setBankError] = useState("");
  const [editing, setEditing] = useState(null);

  // Snapshots state
  const [snapshots, setSnapshots] = useState({ items: [], count: 0 });
  const [snapshotsLoading, setSnapshotsLoading] = useState(false);
  const [snapshotsError, setSnapshotsError] = useState("");

  // Inspector state
  const [inspectorUserId, setInspectorUserId] = useState("");

  // Queue state
  const [queue, setQueue] = useState({ items: [], count: 0 });
  const [queueStatus, setQueueStatus] = useState("all");
  const [queueLoading, setQueueLoading] = useState(false);
  const [queueError, setQueueError] = useState("");

  // Events state
  const [events, setEvents] = useState({ items: [], count: 0 });
  const [eventsFilters, setEventsFilters] = useState({ user_id: "", event_type: "", processed: "" });
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState("");

  const { run: runQuestionMutation, busy: questionBusy } = useApiAction();
  const { run: runQueueProcess, busy: queueProcessing } = useApiAction();

  const loadOverview = useCallback(async () => {
    setOverviewError("");
    try {
      const d = await api.get("/api/admin/persona/overview");
      setOverview(d);
    } catch (e) {
      setOverviewError(e?.message || "Could not load overview");
    }
  }, []);

  const loadBank = useCallback(async () => {
    setBankLoading(true);
    setBankError("");
    try {
      const params = new URLSearchParams();
      params.set("active", bankActiveFilter);
      if (bankQuery.trim()) params.set("q", bankQuery.trim());
      params.set("limit", "100");
      const d = await api.get(`/api/admin/persona/question-bank?${params.toString()}`);
      setBank({ items: d?.items || [], count: d?.count || 0 });
    } catch (e) {
      setBankError(e?.message || "Could not load question bank");
    } finally {
      setBankLoading(false);
    }
  }, [bankActiveFilter, bankQuery]);

  const loadSnapshots = useCallback(async () => {
    setSnapshotsLoading(true);
    setSnapshotsError("");
    try {
      const d = await api.get(`/api/admin/persona/snapshots?limit=50`);
      setSnapshots({ items: d?.items || [], count: d?.count || 0 });
    } catch (e) {
      setSnapshotsError(e?.message || "Could not load snapshots");
    } finally {
      setSnapshotsLoading(false);
    }
  }, []);

  const loadQueue = useCallback(async () => {
    setQueueLoading(true);
    setQueueError("");
    try {
      const params = new URLSearchParams({ status: queueStatus, limit: "100" });
      const d = await api.get(`/api/admin/persona/recompute-queue?${params.toString()}`);
      setQueue({ items: d?.items || [], count: d?.count || 0 });
    } catch (e) {
      setQueueError(e?.message || "Could not load recompute queue");
    } finally {
      setQueueLoading(false);
    }
  }, [queueStatus]);

  const loadEvents = useCallback(async () => {
    setEventsLoading(true);
    setEventsError("");
    try {
      const params = new URLSearchParams({ limit: "100" });
      if (eventsFilters.user_id.trim()) params.set("user_id", eventsFilters.user_id.trim());
      if (eventsFilters.event_type.trim()) params.set("event_type", eventsFilters.event_type.trim());
      if (eventsFilters.processed) params.set("processed", eventsFilters.processed);
      const d = await api.get(`/api/admin/persona/signal-events?${params.toString()}`);
      setEvents({ items: d?.items || [], count: d?.count || 0 });
    } catch (e) {
      setEventsError(e?.message || "Could not load signal events");
    } finally {
      setEventsLoading(false);
    }
  }, [eventsFilters]);

  useEffect(() => {
    if (tab === "overview") loadOverview();
    if (tab === "questions") loadBank();
    if (tab === "snapshots") loadSnapshots();
    if (tab === "queue") loadQueue();
    if (tab === "events") loadEvents();
  }, [tab, loadOverview, loadBank, loadSnapshots, loadQueue, loadEvents]);

  async function patchQuestion(payload) {
    if (!editing) return;
    await runQuestionMutation({
      action: () =>
        api.patch(
          `/api/admin/persona/question-bank/${encodeURIComponent(editing.question_key)}`,
          payload,
        ),
      successMessage: "Question updated",
      errorMessage: "Patch failed",
      onSuccess: () => {
        setEditing(null);
        loadBank();
      },
    });
  }

  async function toggleActive(question) {
    await runQuestionMutation({
      action: () =>
        api.patch(
          `/api/admin/persona/question-bank/${encodeURIComponent(question.question_key)}`,
          { is_active: !question.is_active },
        ),
      errorMessage: "Toggle failed",
      onSuccess: () => loadBank(),
    });
  }

  async function processQueue(limit) {
    await runQueueProcess({
      action: () =>
        api.post("/api/admin/persona/recompute-queue/process", { limit: limit || 25 }),
      successMessage: "Queue processing triggered",
      errorMessage: "Could not process queue",
      onSuccess: () => {
        loadQueue();
        loadOverview();
      },
    });
  }

  function gotoInspector(userId) {
    setInspectorUserId(userId);
    setTab("inspector");
  }

  return (
    <div className="space-y-6" data-testid="admin-persona-page">
      <PageHeader
        eyebrow={
          <span className="inline-flex items-center gap-2">
            <Compass className="h-3.5 w-3.5" /> Persona controls · internal
          </span>
        }
        title="Persona Controls"
        sub="Inspect progressive questions, persona snapshots, and Study OS policy outputs. Persona is internal personalization metadata — not identity, diagnosis, eligibility truth, or recruitment truth."
        right={<StatusDot state="live" label="Live · /api/admin/persona" />}
      />

      <AdminSafetyBanner
        title="Internal personalization metadata"
        testId="admin-persona-safety"
      >
        Persona snapshots are internal personalization metadata. They must not
        override deterministic eligibility results or official recruitment data,
        and persona labels are never shown to users as identity copy.
        This page is read-light: no AI, no exam intelligence, no profile edits.
      </AdminSafetyBanner>

      <nav
        className="flex flex-wrap gap-1 bg-[#F3EADB] p-1 rounded-full border border-[#E7DECB] w-fit"
        aria-label="Persona tabs"
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            data-testid={`admin-persona-tab-${t.id}`}
            className={`px-3.5 py-1.5 rounded-full text-[12px] font-semibold transition ${
              tab === t.id
                ? "bg-[#FFFDF9] text-[#2E2218] border border-[#D9C7A7]"
                : "text-clay-700 hover:bg-[#E7D6BA]"
            }`}
            aria-pressed={tab === t.id}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" ? (
        <section>
          {overviewError ? (
            <div className="rounded-xl bg-dusk-50 text-dusk-800 text-xs px-3 py-2 mb-3">
              {overviewError}
            </div>
          ) : null}
          <PersonaOverviewCards overview={overview} />
        </section>
      ) : null}

      {tab === "questions" ? (
        <section className="space-y-3">
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-sm">
              <span className="text-muted-foreground text-xs">Filter</span>
              <select
                className="mt-1 block rounded-xl border border-clay-200 px-3 py-2 text-sm"
                value={bankActiveFilter}
                onChange={(e) => setBankActiveFilter(e.target.value)}
              >
                <option value="all">All</option>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </label>
            <label className="text-sm flex-1 min-w-[200px]">
              <span className="text-muted-foreground text-xs">Search</span>
              <input
                type="search"
                className="mt-1 w-full rounded-xl border border-clay-200 px-3 py-2 text-sm"
                value={bankQuery}
                placeholder="question_key, text, dimension"
                onChange={(e) => setBankQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadBank()}
              />
            </label>
            <button type="button" onClick={loadBank} className="btn btn-ghost">
              {bankLoading ? "Loading…" : "Refresh"}
            </button>
          </div>
          {bankError ? (
            <div className="rounded-xl bg-dusk-50 text-dusk-800 text-xs px-3 py-2 flex items-center justify-between gap-2">
              <span>{bankError}</span>
              <button type="button" className="btn btn-ghost text-xs" onClick={loadBank}>Retry</button>
            </div>
          ) : null}
          {!bankLoading && !bankError ? (
            <PersonaQuestionBankTable
              items={bank.items}
              onEdit={(q) => setEditing(q)}
              onToggleActive={toggleActive}
            />
          ) : null}
          {editing ? (
            <PersonaQuestionEditor
              question={editing}
              error=""
              saving={questionBusy}
              onClose={() => setEditing(null)}
              onSave={patchQuestion}
            />
          ) : null}
        </section>
      ) : null}

      {tab === "snapshots" ? (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Latest {snapshots.items.length} snapshots — most recent first.
            </p>
            <button type="button" onClick={loadSnapshots} className="btn btn-ghost text-xs">
              {snapshotsLoading ? "Loading…" : "Refresh"}
            </button>
          </div>
          {snapshotsError ? (
            <div className="rounded-xl bg-dusk-50 text-dusk-800 text-xs px-3 py-2 flex items-center justify-between gap-2">
              <span>{snapshotsError}</span>
              <button type="button" className="btn btn-ghost text-xs" onClick={loadSnapshots}>Retry</button>
            </div>
          ) : null}
          {!snapshotsLoading && !snapshotsError ? (
            <PersonaSnapshotTable items={snapshots.items} onInspectUser={gotoInspector} />
          ) : null}
        </section>
      ) : null}

      {tab === "inspector" ? <PersonaUserInspector initialUserId={inspectorUserId} /> : null}

      {tab === "queue" ? (
        <section className="space-y-3">
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-sm">
              <span className="text-muted-foreground text-xs">Status</span>
              <select
                className="mt-1 block rounded-xl border border-clay-200 px-3 py-2 text-sm"
                value={queueStatus}
                onChange={(e) => setQueueStatus(e.target.value)}
              >
                <option value="all">All</option>
                <option value="pending">Pending</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </label>
            <button type="button" onClick={loadQueue} className="btn btn-ghost">
              {queueLoading ? "Loading…" : "Refresh"}
            </button>
          </div>
          {queueError ? (
            <div className="rounded-xl bg-dusk-50 text-dusk-800 text-xs px-3 py-2 flex items-center justify-between gap-2">
              <span>{queueError}</span>
              <button type="button" className="btn btn-ghost text-xs" onClick={loadQueue}>Retry</button>
            </div>
          ) : null}
          {!queueLoading && !queueError ? (
            <PersonaQueueTable
              items={queue.items}
              onProcess={processQueue}
              processing={queueProcessing}
            />
          ) : null}
        </section>
      ) : null}

      {tab === "events" ? (
        <section className="space-y-3">
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-sm flex-1 min-w-[180px]">
              <span className="text-muted-foreground text-xs">User id</span>
              <input
                type="text"
                className="mt-1 w-full rounded-xl border border-clay-200 px-3 py-2 text-sm font-mono"
                value={eventsFilters.user_id}
                onChange={(e) => setEventsFilters((f) => ({ ...f, user_id: e.target.value }))}
              />
            </label>
            <label className="text-sm flex-1 min-w-[180px]">
              <span className="text-muted-foreground text-xs">Event type</span>
              <input
                type="text"
                className="mt-1 w-full rounded-xl border border-clay-200 px-3 py-2 text-sm font-mono"
                value={eventsFilters.event_type}
                onChange={(e) => setEventsFilters((f) => ({ ...f, event_type: e.target.value }))}
                placeholder="persona_question_answered"
              />
            </label>
            <label className="text-sm">
              <span className="text-muted-foreground text-xs">Processed</span>
              <select
                className="mt-1 block rounded-xl border border-clay-200 px-3 py-2 text-sm"
                value={eventsFilters.processed}
                onChange={(e) => setEventsFilters((f) => ({ ...f, processed: e.target.value }))}
              >
                <option value="">Any</option>
                <option value="false">Unprocessed only</option>
                <option value="true">Processed only</option>
              </select>
            </label>
            <button type="button" onClick={loadEvents} className="btn btn-ghost">
              {eventsLoading ? "Loading…" : "Refresh"}
            </button>
          </div>
          {eventsError ? (
            <div className="rounded-xl bg-dusk-50 text-dusk-800 text-xs px-3 py-2 flex items-center justify-between gap-2">
              <span>{eventsError}</span>
              <button type="button" className="btn btn-ghost text-xs" onClick={loadEvents}>Retry</button>
            </div>
          ) : null}
          {!eventsLoading && !eventsError ? (
            <PersonaSignalEventsTable items={events.items} />
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

