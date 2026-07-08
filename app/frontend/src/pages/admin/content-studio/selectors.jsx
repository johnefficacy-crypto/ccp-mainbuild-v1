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
import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { contentStudioApi } from "./contentStudioApi";

// Load an {items:[…]} option feed. `enabled=false` yields an empty list without
// a request (dependent selects waiting on a parent). Errors degrade to [] — the
// operator can still see the currently-selected id and any static fallback.
export function useOptions(loader, deps, enabled = true) {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let alive = true;
    if (!enabled) {
      setOptions([]);
      return undefined;
    }
    setLoading(true);
    Promise.resolve()
      .then(loader)
      .then((d) => { if (alive) setOptions(Array.isArray(d?.items) ? d.items : []); })
      .catch(() => { if (alive) setOptions([]); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { options, loading };
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

export function SubjectSelect({ value, onChange, testId = "select-subject" }) {
  const { options } = useOptions(() => contentStudioApi.listSubjects(), []);
  return (
    <Select value={value} onChange={onChange} testId={testId} placeholder="— Select subject —">
      {options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </Select>
  );
}
SubjectSelect.propTypes = { value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string };

export function TopicSelect({ subjectId, value, onChange, testId = "select-topic" }) {
  const { options } = useOptions(
    () => contentStudioApi.listTopics({ subject_id: subjectId, level: "topic" }),
    [subjectId],
    !!subjectId,
  );
  return (
    <Select
      value={value}
      onChange={onChange}
      disabled={!subjectId}
      testId={testId}
      placeholder={subjectId ? "— Select topic —" : "Select a subject first"}
    >
      {options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </Select>
  );
}
TopicSelect.propTypes = {
  subjectId: PropTypes.string, value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string,
};

export function MicrotopicSelect({ topicId, value, onChange, testId = "select-microtopic" }) {
  const { options } = useOptions(
    () => contentStudioApi.listTopics({ parent_topic_id: topicId, level: "microtopic" }),
    [topicId],
    !!topicId,
  );
  return (
    <Select
      value={value}
      onChange={onChange}
      disabled={!topicId}
      testId={testId}
      placeholder={topicId ? "— None (optional) —" : "Select a topic first"}
    >
      {options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </Select>
  );
}
MicrotopicSelect.propTypes = {
  topicId: PropTypes.string, value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string,
};

export function RubricSelect({ value, onChange, testId = "select-rubric" }) {
  const { options } = useOptions(() => contentStudioApi.listRubrics(), []);
  return (
    <Select value={value} onChange={onChange} testId={testId} placeholder="— None (optional) —">
      {options.map((o) => (
        <option key={o.id} value={o.id}>{o.version ? `${o.name} v${o.version}` : o.name}</option>
      ))}
    </Select>
  );
}
RubricSelect.propTypes = { value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string };

export function SourceDocumentSelect({ value, onChange, testId = "select-source-document" }) {
  const { options } = useOptions(() => contentStudioApi.listSourceDocuments(), []);
  return (
    <Select value={value} onChange={onChange} testId={testId} placeholder="— None (optional) —">
      {options.map((o) => (
        <option key={o.id} value={o.id}>{o.title || o.original_filename || o.id}</option>
      ))}
    </Select>
  );
}
SourceDocumentSelect.propTypes = { value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string };

export function ExamFamilySelect({ value, onChange, testId = "select-exam-family" }) {
  const { options } = useOptions(() => contentStudioApi.listExamFamilies(), []);
  return (
    <Select value={value} onChange={onChange} testId={testId} placeholder="— Select exam family —">
      {options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </Select>
  );
}
ExamFamilySelect.propTypes = { value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string };

export function ExamSelect({ familyId, value, onChange, testId = "select-exam" }) {
  const { options } = useOptions(
    () => contentStudioApi.listExams(familyId ? { exam_family_id: familyId } : {}),
    [familyId],
  );
  return (
    <Select value={value} onChange={onChange} testId={testId} placeholder="— Select exam —">
      {options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </Select>
  );
}
ExamSelect.propTypes = {
  familyId: PropTypes.string, value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string,
};

export function ExamPhaseSelect({ examId, value, onChange, testId = "select-exam-phase" }) {
  const { options } = useOptions(
    () => contentStudioApi.listExamPhases({ exam_id: examId }),
    [examId],
    !!examId,
  );
  return (
    <Select
      value={value}
      onChange={onChange}
      disabled={!examId}
      testId={testId}
      placeholder={examId ? "— Select phase —" : "Select an exam first"}
    >
      {options.map((o) => <option key={o.id} value={o.id}>{o.phase_name}</option>)}
    </Select>
  );
}
ExamPhaseSelect.propTypes = {
  examId: PropTypes.string, value: PropTypes.string, onChange: PropTypes.func.isRequired, testId: PropTypes.string,
};
