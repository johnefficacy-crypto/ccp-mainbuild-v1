import React, { useState } from "react";
import PropTypes from "prop-types";
import { Link, useNavigate } from "react-router-dom";
import { Layers } from "lucide-react";

import { api } from "../../lib/api";
import useApiAction from "../../lib/hooks/useApiAction";
import useApiCollection from "../../lib/hooks/useApiCollection";
import { LoadingSkeleton, EmptyState, ErrorState } from "../../shared/ui/core";
import { TopicRadarChart } from "./components/reports";

const TREND_LABEL = { up: "↑ improving", down: "↓ declining", flat: "→ steady" };

const NO_PRACTICE_COPY = "No verified practice set yet";

// GA weekly current-affairs launch outcomes that have no runnable attempt this cycle.
// The backend returns 200 with an `outcome` (and no `route`) rather than a hard error,
// so the card shows a calm inline note instead of the generic error toast.
const CA_STATE_COPY = {
  no_bundle: "No current-affairs set is published for your exam yet. Check back soon.",
  empty_bundle: "This week's current-affairs set has no questions yet.",
  bundle_degraded: "This week's current-affairs set is being refreshed. Check back soon.",
  already_submitted: "You've already completed this week's current-affairs practice.",
};

// A subject card: keeps the mastery summary line (progress / weak / topics +
// trend) and, below it, renders the subject's practice modes. Server-launch
// modes POST the launch endpoint through useApiAction and navigate to the
// returned route; an expected 409 (empty/unprojected pool) is caught inside the
// action and surfaced as a calm inline note rather than the generic error toast
// (mirrors PyqExplorerSection.startPaperPractice). Client-route modes are plain
// react-router links — no POST.
function SubjectPracticeCard({ subject }) {
  const navigate = useNavigate();
  const { run, busy } = useApiAction();
  const [practiceError, setPracticeError] = useState("");
  const [pendingMode, setPendingMode] = useState(null);

  const subjectId = subject.subject_id || subject.subject;
  const practice = subject.practice || {};
  const modes = practice.available && Array.isArray(practice.modes) ? practice.modes : [];

  const launch = async (mode) => {
    if (busy) return;
    setPendingMode(mode.type);
    setPracticeError("");
    await run({
      action: async () => {
        try {
          return await api.post(`/api/study/subjects/${subjectId}/practice/start`, {
            mode: mode.launch_mode,
            topic_id: mode.target_topic_id ?? null,
          });
        } catch (e) {
          if (e?.status === 409) return { noPractice: true };
          throw e;
        }
      },
      onSuccess: (out) => {
        if (out?.noPractice) {
          setPracticeError(`${NO_PRACTICE_COPY}.`);
          return;
        }
        if (out?.route) {
          navigate(out.route);
          return;
        }
        // GA current-affairs: a non-route outcome (no_bundle/empty/degraded/…) maps to
        // a specific calm note; any other routeless response falls back to the default.
        if (out?.outcome && CA_STATE_COPY[out.outcome]) {
          setPracticeError(CA_STATE_COPY[out.outcome]);
          return;
        }
        setPracticeError(`${NO_PRACTICE_COPY}.`);
      },
      errorMessage: "Couldn't start practice. Please try again.",
    });
    setPendingMode(null);
  };

  return (
    <div className="rounded border p-3 text-left" data-testid={`subject-card-${subjectId}`}>
      <div className="flex items-center justify-between">
        <span className="font-medium">{subject.subject}</span>
        <span className="text-xs text-slate-500">
          {TREND_LABEL[subject.trend] || subject.trend}
        </span>
      </div>
      <div className="text-sm text-slate-600">
        {subject.progress}% mastery · {subject.weak_count} weak · {subject.locked_topics} topics
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {modes.length === 0 ? (
          <span
            className="text-xs text-slate-500"
            data-testid={`practice-${subjectId}-none`}
          >
            {NO_PRACTICE_COPY}
          </span>
        ) : (
          modes.map((mode) =>
            mode.route_type === "client_route" ? (
              <Link
                key={mode.type}
                to={mode.route}
                className="btn btn-ghost text-xs"
                data-testid={`practice-${subjectId}-${mode.type}`}
              >
                {mode.label}
              </Link>
            ) : (
              <button
                key={mode.type}
                type="button"
                onClick={() => launch(mode)}
                disabled={busy}
                aria-busy={busy && pendingMode === mode.type}
                className="btn btn-ghost text-xs disabled:opacity-40"
                data-testid={`practice-${subjectId}-${mode.type}`}
              >
                {busy && pendingMode === mode.type ? "Starting…" : mode.label}
              </button>
            ),
          )
        )}
      </div>

      {practiceError ? (
        <p
          className="mt-2 text-xs text-clay-700"
          data-testid={`practice-${subjectId}-notice`}
          role="status"
        >
          {practiceError}
        </p>
      ) : null}
    </div>
  );
}

SubjectPracticeCard.propTypes = {
  subject: PropTypes.shape({
    subject_id: PropTypes.string,
    subject: PropTypes.string,
    progress: PropTypes.number,
    trend: PropTypes.string,
    weak_count: PropTypes.number,
    locked_topics: PropTypes.number,
    practice: PropTypes.shape({
      available: PropTypes.bool,
      modes: PropTypes.arrayOf(
        PropTypes.shape({
          type: PropTypes.string,
          label: PropTypes.string,
          target_topic_id: PropTypes.string,
          route_type: PropTypes.oneOf(["server_launch", "client_route"]),
          route: PropTypes.string,
          launch_mode: PropTypes.string,
        }),
      ),
    }),
  }).isRequired,
};

export default function Subjects() {
  const { items, status, refresh } = useApiCollection("/api/study/subjects");

  const radar = items
    .slice(0, 10)
    .map((i) => ({ topic: i.subject || i.subject_id, mastery: i.progress || 0 }));

  return (
    <section className="space-y-4" data-testid="subjects-page">
      <h1 className="font-heading text-3xl">Subject practice hub</h1>

      {status === "loading" ? (
        <LoadingSkeleton />
      ) : status === "error" ? (
        <ErrorState
          message="Couldn't load your subjects."
          onRetry={refresh}
        />
      ) : status === "empty" ? (
        <EmptyState
          icon={Layers}
          title="No subjects yet"
          description="Your subject mastery will appear here once you start practicing."
        />
      ) : (
        <>
          <TopicRadarChart data={radar} loading={false} />
          <div className="grid md:grid-cols-2 gap-3">
            {items.map((subject) => (
              <SubjectPracticeCard
                key={subject.subject_id || subject.subject}
                subject={subject}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
