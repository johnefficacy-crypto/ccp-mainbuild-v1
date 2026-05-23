import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Bookmark,
  ChevronRight,
  ShieldCheck,
  RefreshCw,
  AlertCircle,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { api } from "../../lib/api";

// Recruitment listing — queries /api/recruitments, shows apply-window
// stages, fee + save toggle. The deep-link /app/eligibility/recruitments/:id
// fetches GET /api/recruitments/:id and renders the secure detail overlay
// (notification proof, posts, apply window, eligibility preview) returned by
// that endpoint.

const STAGES = ["Notification", "Open", "Closed", "Result"];
const STAGE_INDEX = {
  draft: 0,
  upcoming: 0,
  notification: 0,
  open: 1,
  apply: 1,
  active: 1,
  closed: 2,
  exam: 2,
  result: 3,
  completed: 3,
};

function StatusPill({ status }) {
  const map = {
    eligible: { cls: "pill-sage", label: "Eligible", icon: ShieldCheck },
    conditional: { cls: "pill-dusk", label: "Conditional", icon: AlertCircle },
    urgent: { cls: "pill-clay", label: "Closing soon", icon: Sparkles },
  };
  const cfg = map[status];
  if (!cfg) return null;
  const Icon = cfg.icon;
  return (
    <span className={`pill ${cfg.cls} inline-flex items-center gap-1`}>
      <Icon className="h-3 w-3" /> {cfg.label}
    </span>
  );
}

function fmtDate(d) {
  if (!d) return null;
  const dt = new Date(d);
  if (Number.isNaN(dt.getTime())) return String(d);
  return dt.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

const VERDICT = {
  eligible: { cls: "pill-sage", label: "Eligible", icon: ShieldCheck },
  conditional: { cls: "pill-dusk", label: "Conditional", icon: AlertCircle },
  pending: { cls: "pill-outline", label: "Complete your profile", icon: Sparkles },
};

function RecruitmentDetail({ detail, loading, err, onSave, onApply }) {
  if (loading) {
    return (
      <div role="status" aria-live="polite" className="space-y-3">
        <div className="soft-card rounded-2xl p-6 animate-pulse h-40" />
        <div className="soft-card rounded-2xl p-6 animate-pulse h-56" />
        <span className="sr-only">Loading recruitment</span>
      </div>
    );
  }
  if (err) {
    return (
      <div
        data-testid="recruitment-detail-error"
        className="soft-card rounded-2xl p-10 text-center text-muted-foreground"
      >
        {err}
      </div>
    );
  }
  if (!detail) return null;

  const elig = detail.eligibility_preview || {};
  const verdict = VERDICT[elig.verdict] || VERDICT.pending;
  const VIcon = verdict.icon;
  const win = detail.applyWindow || {};
  const posts = detail.posts || [];
  const applyUrl = detail.cta?.url || detail.sourceUrl;
  const failReasons = elig.fail_reasons || [];

  return (
    <div className="space-y-4" data-testid="recruitment-detail">
      <div className="soft-card rounded-2xl p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0">
            <div className="text-xs uppercase tracking-widest text-muted-foreground">
              {detail.organization || "—"}
            </div>
            <h3 className="font-heading text-2xl font-semibold mt-1">
              {detail.title || detail.name}
            </h3>
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              <span className={`pill ${verdict.cls} inline-flex items-center gap-1`}>
                <VIcon className="h-3 w-3" /> {verdict.label}
              </span>
              {Number.isFinite(elig.total_posts) && (
                <span className="text-xs text-muted-foreground">
                  {elig.matched_posts ?? 0}/{elig.total_posts} posts matched
                </span>
              )}
              {detail.vacancies != null && (
                <span className="text-xs text-muted-foreground">
                  · {Number(detail.vacancies).toLocaleString("en-IN")} vacancies
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onSave}
              data-testid="detail-save"
              className={`h-10 w-10 grid place-items-center rounded-xl border transition ${
                detail.saved
                  ? "bg-clay-500 border-clay-500 text-white"
                  : "border-border hover:border-clay-300"
              }`}
              aria-pressed={!!detail.saved}
              aria-label={detail.saved ? "Saved" : "Save recruitment"}
            >
              <Bookmark className="h-4 w-4" />
            </button>
            {applyUrl && (
              <button
                type="button"
                onClick={onApply}
                data-testid="detail-apply"
                className="btn btn-primary inline-flex items-center gap-1.5"
              >
                {detail.cta?.label || "Apply on official portal"}
                <ExternalLink className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="soft-card rounded-2xl p-5">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
            Apply window
          </div>
          <div className="text-sm">
            <span className="font-semibold">{fmtDate(win.start) || "TBA"}</span>
            <span className="text-muted-foreground"> → </span>
            <span className="font-semibold">{fmtDate(win.end) || "TBA"}</span>
          </div>
        </div>
        <div className="soft-card rounded-2xl p-5">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
            Official notification
          </div>
          {detail.sourceUrl ? (
            <a
              href={detail.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="detail-notification-url"
              className="text-sm link-under text-clay-700 inline-flex items-center gap-1.5 break-all"
            >
              <ShieldCheck className="h-4 w-4 shrink-0" />
              View official notification
            </a>
          ) : (
            <div className="text-sm text-muted-foreground">Not available</div>
          )}
        </div>
      </div>

      <div className="soft-card rounded-2xl p-5" data-testid="detail-posts">
        <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-3">
          Posts ({posts.length})
        </div>
        {posts.length === 0 ? (
          <div className="text-sm text-muted-foreground">No posts listed yet.</div>
        ) : (
          <ul className="divide-y divide-border">
            {posts.map((p, i) => (
              <li key={i} className="py-2.5 flex items-center justify-between gap-3">
                <span className="text-sm font-medium">{p.name || "—"}</span>
                <span className="text-xs text-muted-foreground">
                  {p.vacancies != null
                    ? `${Number(p.vacancies).toLocaleString("en-IN")} vac`
                    : null}
                  {p.payScale ? ` · ${p.payScale}` : null}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {failReasons.length > 0 && (
        <div className="soft-card rounded-2xl p-5" data-testid="detail-eligibility">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
            Why not yet eligible
          </div>
          <ul className="list-disc pl-5 space-y-1">
            {failReasons.map((r, i) => (
              <li key={i} className="text-sm text-clay-700">
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function EligibleRecruitmentsPage() {
  const { id } = useParams();
  const [data, setData] = useState({ items: [], counts: {} });
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const [recomputing, setRecomputing] = useState(false);
  const [recomputeMsg, setRecomputeMsg] = useState(null);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const qs = new URLSearchParams();
      if (filter !== "all") qs.set("status", filter);
      if (q.trim()) qs.set("q", q.trim());
      const d = await api.get(`/api/recruitments?${qs.toString()}`);
      setData(d || { items: [], counts: {} });
    } catch (e) {
      setErr("Recruitments are temporarily unavailable.");
      if (process.env.NODE_ENV !== "production") console.error(e);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  async function recompute() {
    setRecomputing(true);
    setRecomputeMsg(null);
    try {
      const r = await api.post("/api/eligibility/recompute", {});
      setRecomputeMsg(
        `Recomputed: ${r.processed} posts evaluated · ${r.eligible} eligible · ${r.conditional} conditional`,
      );
      await load();
    } catch (e) {
      setRecomputeMsg(`Recompute failed: ${e.message}`);
    } finally {
      setRecomputing(false);
    }
  }

  async function toggleSave(ev, recruitmentId) {
    ev.preventDefault();
    ev.stopPropagation();
    await api.post(`/api/recruitments/${recruitmentId}/save`, {});
    load();
  }

  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailErr, setDetailErr] = useState("");

  useEffect(() => {
    if (!id) {
      setDetail(null);
      setDetailErr("");
      return undefined;
    }
    let cancelled = false;
    (async () => {
      setDetailLoading(true);
      setDetailErr("");
      try {
        const d = await api.get(`/api/recruitments/${id}`);
        if (!cancelled) setDetail(d);
      } catch (e) {
        if (!cancelled)
          setDetailErr(
            e.status === 404
              ? "Recruitment not found, or it's no longer published."
              : "This recruitment is temporarily unavailable.",
          );
        if (process.env.NODE_ENV !== "production") console.error(e);
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function saveDetail() {
    if (!detail?.id) return;
    await api.post(`/api/recruitments/${detail.id}/save`, {});
    try {
      const d = await api.get(`/api/recruitments/${detail.id}`);
      setDetail(d);
    } catch {
      setDetail((prev) => (prev ? { ...prev, saved: !prev.saved } : prev));
    }
  }

  async function clickApply() {
    if (!detail?.id) return;
    try {
      await api.post(`/api/applications/${detail.id}/clicked-apply`, {});
    } catch (e) {
      if (process.env.NODE_ENV !== "production") console.error(e);
    }
    const url = detail.cta?.url || detail.sourceUrl;
    if (url) window.open(url, "_blank", "noopener,noreferrer");
  }

  const tabs = [
    { id: "all", label: `All · ${data.counts.all ?? 0}` },
    { id: "eligible", label: `Eligible · ${data.counts.eligible ?? 0}` },
    { id: "urgent", label: `Closing soon · ${data.counts.urgent ?? 0}` },
    { id: "conditional", label: `Conditional · ${data.counts.conditional ?? 0}` },
  ];

  const visibleItems = data.items;

  return (
    <section
      data-testid="eligibility-recruitments-page"
      aria-labelledby="eligibility-recruitments-heading"
    >
      <div className="flex items-end justify-between flex-wrap gap-3 mb-4">
        <div>
          <h2
            id="eligibility-recruitments-heading"
            className="font-heading text-2xl font-semibold tracking-tight"
          >
            Open recruitments
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Live cycles matched to your profile by the deterministic eligibility engine.
          </p>
          {id ? (
            <Link
              to="/app/eligibility/recruitments"
              className="text-[12px] font-semibold link-under text-clay-700 mt-2 inline-block"
            >
              ← Back to all recruitments
            </Link>
          ) : null}
        </div>
        {!id && (
          <button
            onClick={recompute}
            disabled={recomputing}
            data-testid="recompute-btn"
            className="btn btn-ghost"
          >
            <RefreshCw className={`h-4 w-4 ${recomputing ? "animate-spin" : ""}`} />
            {recomputing ? "Recomputing…" : "Recompute eligibility"}
          </button>
        )}
      </div>

      {recomputeMsg && (
        <div
          data-testid="recompute-msg"
          className={`rounded-xl p-3 text-xs border mb-3 ${
            recomputeMsg.toLowerCase().includes("failed")
              ? "bg-red-50 border-red-200 text-red-700"
              : "bg-sage-100/60 border-sage-200"
          }`}
        >
          {recomputeMsg}
        </div>
      )}

      {!id && (
        <div className="flex items-center gap-3 flex-wrap mb-4">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Recruitment filters">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={filter === t.id}
                data-testid={`filter-${t.id}`}
                onClick={() => setFilter(t.id)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-clay-500 focus-visible:ring-offset-2 ${
                  filter === t.id
                    ? "bg-clay-500 text-white"
                    : "bg-white/70 border border-border hover:border-clay-300"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              load();
            }}
            className="flex-1 max-w-xs"
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search by name or org…"
              className="w-full px-4 py-2 rounded-full bg-white/80 border border-border text-sm"
              data-testid="recruitments-search"
              aria-label="Search recruitments"
            />
          </form>
        </div>
      )}

      {id ? (
        <RecruitmentDetail
          detail={detail}
          loading={detailLoading}
          err={detailErr}
          onSave={saveDetail}
          onApply={clickApply}
        />
      ) : (
        <>
      {err && <div className="text-xs text-clay-700 mb-3">{err}</div>}

      {loading ? (
        <div role="status" aria-live="polite" className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="soft-card rounded-2xl p-5 animate-pulse h-32" />
          ))}
          <span className="sr-only">Loading recruitments</span>
        </div>
      ) : visibleItems.length === 0 ? (
        <div
          data-testid="recruitments-empty"
          className="soft-card rounded-2xl p-10 text-center text-muted-foreground"
        >
          {id
            ? "Recruitment not found, or it's no longer published."
            : "No published recruitments match this filter yet. "}
          {!id && (
            <button onClick={recompute} className="link-under">
              recomputing eligibility
            </button>
          )}
          {!id && " or check back after the next ingestion run."}
        </div>
      ) : (
        <div className="space-y-3">
          {visibleItems.map((e) => {
            const stageIdx = STAGE_INDEX[(e.stage || "").toLowerCase()] ?? 0;
            const elig = e.eligibility || {};
            const orgCode =
              e.organization_code || (e.organization || "—").slice(0, 4).toUpperCase();
            const close = e.apply_window?.close;
            const closeFmt = close
              ? new Date(close).toLocaleDateString("en-IN", { day: "numeric", month: "short" })
              : null;
            return (
              <Link
                key={e.id}
                to={`/app/eligibility/recruitments/${e.id}`}
                className="block soft-card rounded-2xl p-5 hover:border-clay-300 transition"
                data-testid={`recruitment-${e.id}`}
              >
                <div className="flex items-start gap-5 flex-wrap">
                  <div className="flex items-start gap-4 flex-1 min-w-[280px]">
                    <div className="h-12 w-12 rounded-xl bg-clay-100 grid place-items-center font-heading font-semibold text-xs text-clay-700">
                      {orgCode}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-heading font-semibold text-lg">{e.name}</h3>
                        <StatusPill status={e.status} />
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {e.organization}
                        {e.year ? ` · ${e.year}` : ""}
                      </div>
                      {(elig.fail_reasons || []).length > 0 && (
                        <div className="mt-2 text-xs text-clay-700">{elig.fail_reasons[0]}</div>
                      )}
                      {elig.eligible && (
                        <div className="mt-2 text-xs text-sage-700">
                          You're eligible — apply window{" "}
                          {closeFmt ? `closes ${closeFmt}` : "open"}.
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
                        Vacancies
                      </div>
                      <div className="font-heading font-semibold text-lg">
                        {e.vacancies?.toLocaleString() || "—"}
                      </div>
                    </div>
                    <button
                      onClick={(ev) => toggleSave(ev, e.id)}
                      data-testid={`save-${e.id}`}
                      className={`h-10 w-10 grid place-items-center rounded-xl border transition ${
                        e.saved
                          ? "bg-clay-500 border-clay-500 text-white"
                          : "border-border hover:border-clay-300"
                      }`}
                    >
                      <Bookmark className="h-4 w-4" />
                    </button>
                    <div className="h-10 w-10 grid place-items-center rounded-xl bg-foreground/5">
                      <ChevronRight className="h-4 w-4" />
                    </div>
                  </div>
                </div>

                <div className="mt-5 flex items-center gap-1.5">
                  {STAGES.map((s, i) => {
                    const active = i <= stageIdx;
                    return (
                      <div key={s} className="flex-1">
                        <div
                          className={`h-1.5 rounded-full ${active ? "bg-clay-500" : "bg-clay-100"}`}
                        />
                        <div
                          className={`mt-1.5 text-[10px] uppercase tracking-wider font-semibold ${
                            active ? "text-foreground" : "text-muted-foreground"
                          }`}
                        >
                          {s}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Link>
            );
          })}
        </div>
      )}
        </>
      )}
    </section>
  );
}
