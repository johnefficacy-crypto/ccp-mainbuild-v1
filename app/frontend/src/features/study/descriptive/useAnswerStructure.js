import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../../lib/api";

const BASE = "/api/study/descriptive";

/**
 * The verified answer structure beside one SUBMITTED attempt, and the points
 * the aspirant ticks as covered.
 *
 * The server refuses the structure for a draft (409 `not_submitted`); the
 * surface never asks before submit, but if it did, that refusal is the rule.
 *
 * Ticks save optimistically: the checkbox moves at once, the PUT follows, and
 * a failed save rolls the tick back and says so. The server stores the ids in
 * the structure's own order against the version ticked, so two tabs ticking
 * the same set store the same thing.
 */
export default function useAnswerStructure(attemptId) {
  const [state, setState] = useState("loading"); // loading | ready | error
  const [data, setData] = useState(null);
  const [covered, setCovered] = useState([]);
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const seq = useRef(0);

  useEffect(() => {
    if (!attemptId) return undefined;
    let live = true;
    setState("loading");
    api
      .get(`${BASE}/attempts/${attemptId}/structure`)
      .then((res) => {
        if (!live) return;
        setData(res);
        setCovered(Array.isArray(res?.covered_point_ids) ? res.covered_point_ids : []);
        setState("ready");
      })
      .catch(() => live && setState("error"));
    return () => {
      live = false;
    };
  }, [attemptId]);

  const toggle = useCallback(
    async (pointId) => {
      const version = data?.structure?.version;
      if (!version) return;
      const previous = covered;
      const next = previous.includes(pointId)
        ? previous.filter((p) => p !== pointId)
        : [...previous, pointId];
      setCovered(next);
      setSaveError("");
      setSaving(true);
      const mine = ++seq.current;
      try {
        const res = await api.put(`${BASE}/attempts/${attemptId}/coverage`, {
          structure_version: version,
          covered_point_ids: next,
        });
        // A later toggle already superseded this one; its answer wins.
        if (mine === seq.current) setCovered(res?.covered_point_ids || next);
      } catch (e) {
        if (mine === seq.current) {
          setCovered(previous);
          setSaveError(
            e?.status === 409
              ? "This answer structure was just updated. Reload to tick against the new one."
              : "Couldn't save that tick. Try again.",
          );
        }
      } finally {
        if (mine === seq.current) setSaving(false);
      }
    },
    [attemptId, covered, data],
  );

  const total = data?.structure?.body_points?.length || 0;
  const pct = total ? Math.round((1000 * covered.length) / total) / 10 : null;

  return {
    state,
    structure: data?.structure || null,
    ticksFromOlderVersion: Boolean(data?.ticks_from_older_version),
    covered,
    toggle,
    saving,
    saveError,
    pointsCoveredPct: pct,
  };
}
