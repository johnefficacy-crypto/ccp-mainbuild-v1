import React, { useState } from "react";
import PropTypes from "prop-types";
import { useNavigate } from "react-router-dom";
import { Play } from "lucide-react";

import useEnglishPracticeSession from "./useEnglishPracticeSession";

/**
 * EWP-SP3-UI — learner "launch writing practice" control.
 *
 * Rendered on the writing/English planner task item (see StudyHome). Clicking it
 * calls the SERVER-OWNED launch endpoint (`POST /api/study/tasks/{id}/launch-
 * writing`) through the writing-practice data-layer hook and, on success,
 * navigates the learner to the returned `practice_route` (the existing
 * `/app/study/practice/english/:sessionId` shell — no new route is added).
 *
 * The server alone decides eligibility: this control NEVER computes eligibility
 * client-side and NEVER passes a client-chosen `prompt_id` — everything is
 * derived from the owned task. State machine (idle → launching → success|error):
 *  - success            → navigate to `practice_route`.
 *  - 409 no_eligible_prompt → calm "no practice available for this task yet"
 *    note. This is EXPECTED until prompts are activated, so it is NOT a hard
 *    error and shows no retry.
 *  - 404               → "this task is no longer available" message.
 *  - any other failure → explicit error + Retry (never silent).
 */

const NO_ELIGIBLE_PROMPT = "no_eligible_prompt";

// Read the backend detail string off the thrown api error (see lib/api.js:
// `err.detail` is the raw FastAPI `detail`). Used only to recognise the
// EXPECTED 409 sentinel — not to reconstruct eligibility.
function detailString(err) {
  const d = err?.detail;
  if (typeof d === "string") return d;
  if (d && typeof d === "object" && typeof d.error === "string") return d.error;
  return "";
}

export default function LaunchWritingPracticeButton({ task, label, className }) {
  const navigate = useNavigate();
  const { launchWriting } = useEnglishPracticeSession();
  const [phase, setPhase] = useState("idle"); // idle | launching | no_prompt | not_found | error
  const studyTaskId = task?.id;
  const buttonLabel = label || task?.action_label || "Start writing practice";

  async function launch() {
    if (!studyTaskId || phase === "launching") return;
    setPhase("launching");
    try {
      const result = await launchWriting(studyTaskId);
      const route = result?.practice_route;
      if (!route) {
        // A 2xx with no route is unexpected — surface it rather than navigate
        // nowhere.
        setPhase("error");
        return;
      }
      // Success — hand off to the existing practice shell route. Leave phase in
      // "launching" so the control stays disabled through the navigation.
      navigate(route);
    } catch (err) {
      if (err?.status === 409 && detailString(err).includes(NO_ELIGIBLE_PROMPT)) {
        setPhase("no_prompt");
        return;
      }
      if (err?.status === 404) {
        setPhase("not_found");
        return;
      }
      setPhase("error");
    }
  }

  const launching = phase === "launching";

  if (phase === "no_prompt") {
    return (
      <p
        className="text-[12px] text-clay-700"
        data-testid="launch-writing-no-prompt"
        role="status"
      >
        No practice available for this task yet — check back once prompts are ready.
      </p>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={launch}
        disabled={launching || !studyTaskId}
        aria-busy={launching}
        className={className || "btn btn-primary"}
        data-testid="launch-writing-btn"
      >
        <Play className="h-4 w-4" aria-hidden="true" />
        {launching ? "Starting…" : buttonLabel}
      </button>
      {phase === "not_found" ? (
        <p
          className="text-[12px] text-rose-700"
          data-testid="launch-writing-not-found"
          role="alert"
        >
          This task is no longer available.
        </p>
      ) : null}
      {phase === "error" ? (
        <p
          className="text-[12px] text-rose-700"
          data-testid="launch-writing-error"
          role="alert"
        >
          Couldn&apos;t start practice.{" "}
          <button
            type="button"
            className="link-under"
            onClick={launch}
            data-testid="launch-writing-retry"
          >
            Retry
          </button>
        </p>
      ) : null}
    </div>
  );
}

LaunchWritingPracticeButton.propTypes = {
  // The planner task. Only `id` is required to launch; `action_label` (from
  // mission-control's typed launch target) is used for the button copy.
  task: PropTypes.shape({
    id: PropTypes.string,
    action_label: PropTypes.string,
  }).isRequired,
  label: PropTypes.string,
  className: PropTypes.string,
};
