/**
 * Readable, dependent selector primitives for Content Studio (EWP-SP4).
 *
 * These replace raw-UUID text inputs in the create/edit and assignment forms.
 * Each select still stores/emits the canonical id (subject_id / topic_id /
 * exam_id / exam_phase_id …) — only the human label is surfaced — so the
 * backend FK contract is unchanged and the exactly-one-scope payload rules are
 * untouched. Options load lazily from the Content Studio API source of truth
 * (contentStudioApi); a dependent select stays disabled until its parent is
 * chosen and reloads when the parent changes.
 */
import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { contentStudioApi } from "./contentStudioApi";

// Load an {items:[…]} option feed with the four-state collection contract
// (AGENTS.md → `idle → loading → data | empty | error`). An option feed must
// NOT silently fail-closed to []: an auth/flag/outage/malformed failure surfaces
// as `status: "error"` (with a retry), distinct from a genuinely empty feed, so
// a denied/unavailable picker is never mistaken for "no options."
// `enabled=false` (a dependent select waiting on its parent) reports `idle`.
export function useOptions(loader, deps, enabled = true) {
  const [options, setOptions] = useState([]);
  const [status, setStatus] = useState(enabled ? "loading" : "idle");
  const [error, setError] = useState(null);
  const [nonce, setNonce] = useState(0);
  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let alive = true;
    if (!enabled) {
      setOptions([]);
      setStatus("idle");
      setError(null);
      return undefined;
    }
    setStatus("loading");
    setError(null);
    Promise.resolve()
      .then(loader)
      .then((d) => {
        if (!alive) return;
        const items = Array.isArray(d?.items) ? d.items : [];
        setOptions(items);
        setStatus(items.length ? "live" : "empty");
      })
      .catch((e) => {
        if (!alive) return;
        setOptions([]);
        setError(e);
        setStatus("error");
      });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled, nonce]);

  return { options, status, error, reload, loading: status === "loading" };
}

function Select({ value, onChange, disabled, testId, placeholder, children }) {
  return (
    <select
      className="input"
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      data-testid={testId}
    >
      <option value="">{placeholder}</option>
      {children}
    </select>
  );
}
Select.propTypes = {
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  testId: PropTypes.string,
  placeholder: PropTypes.string,
  children: PropTypes.node,
};

// Renders the loaded options as a <Select>, OR — when the feed failed — an
// explicit error state with a Retry, so a denied/unavailable feed is never
// collapsed into a silent empty dropdown.
function OptionSelect({ result, value, onChange, disabled, testId, placeholder, waitingPlaceholder, children }) {
  const { status, error, reload } = result;
  if (status === "error") {
    return (
      <div role="alert" data-testid={`${testId}-error`} style={{ fontSize: 12, color: "var(--err, #c00)" }}>
        Couldn’t load options{error && error.status ? ` (${error.status})` : ""}.{" "}
        <button type="button" className="btn small" onClick={reload} data-testid={`${testId}-retry`}>
          Retry
        </button>
      </div>
    );
  }
  const isWaiting = status === "idle";
  return (
    <Select
      value={value}
      onChange={onChange}
      disabled={disabled || status === "loading"}
      testId={testId}
      placeholder={isWaiting ? waitingPlaceholder : (status === "loading" ? "Loading…" : placeholder)}
    >
      {children}
    </Select>
  );
}
OptionSelect.propTypes = {
  result: PropTypes.shape({
    status: PropTypes.string,
    error: PropTypes.object,
    reload: PropTypes.func,
  }).isRequired,
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  testId: PropTypes.string,
  placeholder: PropTypes.string,
  waitingPlaceholder: PropTypes.string,
  children: PropTypes.node,
};

export function SubjectSelect({ value, onChange, testId = "select-subject" }) {
  const result = useOptions(() => contentStudioApi.listSubjects(), []);
  return (
    <OptionSelect result={result} value={value} onChange={onChange} testId={testId} placeholder="— Select subject —">
      {result.options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </OptionSelect>
  );
}
SubjectSelect.propTypes = { value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string };

export function TopicSelect({ subjectId, value, onChange, testId = "select-topic" }) {
  const result = useOptions(
    () => contentStudioApi.listTopics({ subject_id: subjectId, level: "topic" }),
    [subjectId],
    !!subjectId,
  );
  return (
    <OptionSelect
      result={result}
      value={value}
      onChange={onChange}
      disabled={!subjectId}
      testId={testId}
      placeholder="— Select topic —"
      waitingPlaceholder="Select a subject first"
    >
      {result.options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </OptionSelect>
  );
}
TopicSelect.propTypes = {
  subjectId: PropTypes.string, value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string,
};

export function MicrotopicSelect({ topicId, value, onChange, testId = "select-microtopic" }) {
  const result = useOptions(
    () => contentStudioApi.listTopics({ parent_topic_id: topicId, level: "microtopic" }),
    [topicId],
    !!topicId,
  );
  return (
    <OptionSelect
      result={result}
      value={value}
      onChange={onChange}
      disabled={!topicId}
      testId={testId}
      placeholder="— None (optional) —"
      waitingPlaceholder="Select a topic first"
    >
      {result.options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </OptionSelect>
  );
}
MicrotopicSelect.propTypes = {
  topicId: PropTypes.string, value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string,
};

export function RubricSelect({ value, onChange, testId = "select-rubric" }) {
  const result = useOptions(() => contentStudioApi.listRubrics(), []);
  return (
    <OptionSelect result={result} value={value} onChange={onChange} testId={testId} placeholder="— None (optional) —">
      {result.options.map((o) => (
        <option key={o.id} value={o.id}>{o.version ? `${o.name} v${o.version}` : o.name}</option>
      ))}
    </OptionSelect>
  );
}
RubricSelect.propTypes = { value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string };

export function SourceDocumentSelect({ value, onChange, testId = "select-source-document" }) {
  const result = useOptions(() => contentStudioApi.listSourceDocuments(), []);
  return (
    <OptionSelect result={result} value={value} onChange={onChange} testId={testId} placeholder="— None (optional) —">
      {result.options.map((o) => (
        <option key={o.id} value={o.id}>{o.title || o.original_filename || o.id}</option>
      ))}
    </OptionSelect>
  );
}
SourceDocumentSelect.propTypes = { value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string };

export function ExamFamilySelect({ value, onChange, testId = "select-exam-family" }) {
  const result = useOptions(() => contentStudioApi.listExamFamilies(), []);
  return (
    <OptionSelect result={result} value={value} onChange={onChange} testId={testId} placeholder="— Select exam family —">
      {result.options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </OptionSelect>
  );
}
ExamFamilySelect.propTypes = { value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string };

export function ExamSelect({ familyId, value, onChange, testId = "select-exam" }) {
  const result = useOptions(
    () => contentStudioApi.listExams(familyId ? { exam_family_id: familyId } : {}),
    [familyId],
  );
  return (
    <OptionSelect result={result} value={value} onChange={onChange} testId={testId} placeholder="— Select exam —">
      {result.options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </OptionSelect>
  );
}
ExamSelect.propTypes = {
  familyId: PropTypes.string, value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string,
};

export function ExamPhaseSelect({ examId, value, onChange, testId = "select-exam-phase" }) {
  const result = useOptions(
    () => contentStudioApi.listExamPhases({ exam_id: examId }),
    [examId],
    !!examId,
  );
  return (
    <OptionSelect
      result={result}
      value={value}
      onChange={onChange}
      disabled={!examId}
      testId={testId}
      placeholder="— Select phase —"
      waitingPlaceholder="Select an exam first"
    >
      {result.options.map((o) => <option key={o.id} value={o.id}>{o.phase_name}</option>)}
    </OptionSelect>
  );
}
ExamPhaseSelect.propTypes = {
  examId: PropTypes.string, value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string,
};
