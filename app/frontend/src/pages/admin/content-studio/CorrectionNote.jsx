/**
 * Author read-back of the reviewer's latest correction note (EWP-SP4).
 *
 * When a prompt is in `needs_correction`, the author needs to see WHY before
 * re-editing. The note lives in the audit log (not on the prompt row); this
 * fetches the latest needs_correction transition via
 * contentStudioApi.getCorrectionNote and renders it READ-ONLY. It never exposes
 * a control that could edit the review record — surfacing only.
 */
import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { contentStudioApi } from "./contentStudioApi";

export default function CorrectionNote({ promptId }) {
  const [note, setNote] = useState(null);
  const [state, setState] = useState("loading"); // loading | ready | none | error

  useEffect(() => {
    let alive = true;
    contentStudioApi
      .getCorrectionNote(promptId)
      .then((d) => {
        if (!alive) return;
        if (d && d.note) { setNote(d.note); setState("ready"); }
        else setState("none");
      })
      .catch(() => { if (alive) setState("error"); });
    return () => { alive = false; };
  }, [promptId]);

  if (state === "loading" || state === "none" || state === "error") return null;

  const when = note.created_at ? new Date(note.created_at).toLocaleString() : null;

  return (
    <div
      role="note"
      aria-label="Reviewer correction note"
      data-testid="correction-note"
      style={{
        border: "1px solid var(--warn-rule, #e0b000)",
        background: "var(--warn-bg, #fff8e1)",
        borderRadius: 4,
        padding: "0.6rem 0.75rem",
        marginBottom: 12,
        fontSize: 12,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4 }}>
        Reviewer requested corrections
      </div>
      {note.reviewer_notes ? (
        <div style={{ whiteSpace: "pre-wrap", marginBottom: 4 }} data-testid="correction-note-text">
          {note.reviewer_notes}
        </div>
      ) : (
        <div style={{ opacity: 0.75, marginBottom: 4 }} data-testid="correction-note-text">
          No detailed note was left — see the recorded reason below.
        </div>
      )}
      {note.reason ? (
        <div style={{ opacity: 0.85 }}>
          <span style={{ opacity: 0.7 }}>Reason: </span>{note.reason}
        </div>
      ) : null}
      <div style={{ opacity: 0.6, marginTop: 4 }}>
        {note.actor_email ? `by ${note.actor_email}` : ""}{when ? ` · ${when}` : ""}
      </div>
    </div>
  );
}

CorrectionNote.propTypes = {
  promptId: PropTypes.string.isRequired,
};
