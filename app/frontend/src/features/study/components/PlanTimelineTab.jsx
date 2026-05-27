import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { History } from "lucide-react";
import { api } from "../../../lib/api";
import { Card, Eyebrow, StatusDot, StudyEmptyState } from "../../../shared/ui/studyos";
import PlanImpactTimeline from "../../../pages/study/components/reports/PlanImpactTimeline";

const KIND_TITLE = {
  topic_added: "Topic added",
  topic_removed: "Topic removed",
  priority_shift: "Priority shift",
  phase_change: "Phase change",
};

function formatAt(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.valueOf())) return String(iso);
  return d.toLocaleString();
}

function toItem(event) {
  const trigger = event.trigger || {};
  const isMock = trigger.type === "mock_attempt" && Boolean(trigger.attempt_id);
  const delta = event.mastery_delta_db ? Number(event.mastery_delta_db.delta) : undefined;
  return {
    id: event.id,
    at: formatAt(event.at),
    title: KIND_TITLE[event.kind] || "Plan change",
    description: event.reason_human || "",
    clickable: isMock,
    attempt_id: trigger.attempt_id,
    mastery_delta: Number.isFinite(delta) ? delta : undefined,
  };
}

export default function PlanTimelineTab() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    api
      .get("/api/study/reports/plan-timeline?days=90")
      .then((d) => {
        if (cancelled) return;
        setEvents(Array.isArray(d?.events) ? d.events : []);
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setErr(e?.message || "Couldn't load plan changes.");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const items = events.map(toItem);
  const onSelect = (item) => {
    if (item.attempt_id) {
      navigate(`/app/study/mocks/attempts/${item.attempt_id}/result`);
    }
  };

  return (
    <Card padded={false} data-testid="plan-timeline-tab">
      <div className="px-7 pt-6 pb-3 flex items-end justify-between gap-4">
        <div>
          <Eyebrow>Plan changes</Eyebrow>
          <h2 className="font-heading text-[18px] mt-1 flex items-center gap-2">
            <History className="h-4 w-4 text-clay-700" aria-hidden="true" />
            Why your plan changed
          </h2>
        </div>
        <StatusDot state="live" label="" />
      </div>
      <div className="hairline mx-7" />
      <div className="px-7 py-5">
        {err ? (
          <p className="text-sm text-clay-700" data-testid="plan-timeline-error">
            {err}
          </p>
        ) : loading ? (
          <p className="text-sm text-clay-700">Loading plan changes…</p>
        ) : items.length === 0 ? (
          <StudyEmptyState
            icon="·"
            title="No plan changes yet"
            body="When the planner adapts your schedule — after a mock, a missed task, or a deadline shift — the change shows up here with its reason."
          />
        ) : (
          <PlanImpactTimeline items={items} onSelect={onSelect} />
        )}
      </div>
    </Card>
  );
}
