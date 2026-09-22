import PropTypes from "prop-types";
import React, { useEffect, useState } from "react";

import { api } from "../../../lib/api";
import { Card, Eyebrow } from "../../../shared/ui/studyos";

/**
 * The open draft, offered back.
 *
 * There is at most one — the database enforces one open draft per question per
 * user — and it is the single most likely thing the aspirant came back for. It
 * sits above the catalogue because making someone navigate to a subject, a
 * paper and a theme to reach the answer they were halfway through is asking
 * them to re-find their own place.
 *
 * The subject is in the breadcrumb, always. This card is the one place a
 * question appears with no subject chosen, so its label has to carry one.
 */
export default function ContinueCard({ onResume }) {
  const [draft, setDraft] = useState(null);

  useEffect(() => {
    let live = true;
    api
      .get("/api/study/descriptive/attempts?status=draft&limit=1")
      .then((d) => {
        if (!live) return;
        const items = Array.isArray(d?.items) ? d.items : [];
        setDraft(items[0] || null);
      })
      // Silent: a Continue card that cannot load is a card that does not
      // appear. It is a shortcut, and a broken shortcut must not become an
      // error message in front of the catalogue.
      .catch(() => live && setDraft(null));
    return () => {
      live = false;
    };
  }, []);

  if (!draft?.question?.id) return null;

  const subject = draft.question.subject;
  const source = draft.question.breadcrumb?.source;

  return (
    <Card>
      <Eyebrow>Where you left off</Eyebrow>
      <p className="mt-1 text-[13px] leading-snug" data-testid="descriptive-continue-excerpt">
        {draft.question.excerpt}
      </p>
      <p className="num-mono mt-1 text-[10.5px] text-clay-700" data-testid="descriptive-continue-crumb">
        {[subject, source].filter(Boolean).join(" · ")}
      </p>
      <button
        type="button"
        className="btn btn-primary mt-3"
        onClick={() => onResume(draft.question.id)}
        data-testid="descriptive-continue-resume"
      >
        Resume
      </button>
    </Card>
  );
}

ContinueCard.propTypes = { onResume: PropTypes.func.isRequired };
