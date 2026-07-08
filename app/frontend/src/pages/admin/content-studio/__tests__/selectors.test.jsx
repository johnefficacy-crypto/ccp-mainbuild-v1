import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Transport + action-hook stubs (same posture as ContentStudio.test.jsx).
jest.mock("../../../../lib/api", () => ({
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
  getApiErrorMessage: (e) => e?.message || "error",
}));
// useApiAction here INVOKES the action so we can assert the posted payload.
jest.mock("../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({
    run: jest.fn(async ({ action, onSuccess }) => {
      await action();
      if (onSuccess) onSuccess();
      return { ok: true };
    }),
    busy: false,
  }),
}));

// eslint-disable-next-line global-require, import/first
const { api } = require("../../../../lib/api");
// eslint-disable-next-line global-require, import/first
import {
  SubjectSelect, TopicSelect, MicrotopicSelect, ExamSelect, ExamPhaseSelect, RubricSelect,
} from "../selectors";
// eslint-disable-next-line import/first
import ExamAssignments, { scopeLabel } from "../ExamAssignments";
// eslint-disable-next-line import/first
import CorrectionNote from "../CorrectionNote";

const SUBJ = "11111111-1111-4111-8111-111111111111";
const TOPIC = "22222222-2222-4222-8222-222222222222";
const FAM = "44444444-4444-4444-8444-444444444444";
const EXAM = "55555555-5555-4555-8555-555555555555";
const PHASE = "66666666-6666-4666-8666-666666666666";
const PROMPT = "77777777-7777-4777-8777-777777777777";
const RUB = "88888888-8888-4888-8888-888888888888";

function routeGet(overrides = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/taxonomy/subjects")) return Promise.resolve({ items: [{ id: SUBJ, name: "English" }] });
    if (url.includes("/taxonomy/topics")) return Promise.resolve({ items: [{ id: TOPIC, name: "Reading Comprehension" }] });
    if (url.includes("/exam-scope/families")) return Promise.resolve({ items: [{ id: FAM, name: "SSC" }] });
    if (url.includes("/exam-scope/exams")) return Promise.resolve({ items: [{ id: EXAM, name: "SSC CGL", exam_family_id: FAM }] });
    if (url.includes("/exam-scope/phases")) return Promise.resolve({ items: [{ id: PHASE, phase_name: "Tier 1", exam_id: EXAM }] });
    if (url.includes("/rubrics")) return Promise.resolve({ items: [{ id: RUB, name: "Essay", version: 2 }] });
    if (url.includes("/source-documents")) return Promise.resolve({ items: [{ id: "d1", title: "Syllabus" }] });
    if (url.includes("/correction-note")) return Promise.resolve(overrides.correctionNote ?? { note: null });
    if (url.includes("/targets")) return Promise.resolve(overrides.targets ?? { items: [] });
    if (/writing-prompts\/[^/]+$/.test(url)) {
      return Promise.resolve(overrides.prompt ?? {
        id: PROMPT, exercise_type: "essay_practice", difficulty_level: 4, reviewer_status: "pending",
        prompt_text: "Write an essay.", subject_name: "English", topic_name: "Reading Comprehension",
      });
    }
    return Promise.resolve({ items: [] });
  });
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  routeGet();
  api.post.mockResolvedValue({ ok: true });
});

describe("taxonomy selectors render readable options", () => {
  test("SubjectSelect lists subject names, not UUIDs", async () => {
    render(<SubjectSelect value="" onChange={() => {}} />);
    expect(await screen.findByText("English")).toBeInTheDocument();
    expect(screen.queryByText(SUBJ)).toBeNull();
  });

  test("RubricSelect shows name + version", async () => {
    render(<RubricSelect value="" onChange={() => {}} />);
    expect(await screen.findByText("Essay v2")).toBeInTheDocument();
  });
});

describe("dependent filtering", () => {
  test("TopicSelect is disabled without a subject and queries by subject_id once given", async () => {
    const { rerender } = render(<TopicSelect subjectId="" value="" onChange={() => {}} />);
    expect(screen.getByTestId("select-topic")).toBeDisabled();

    rerender(<TopicSelect subjectId={SUBJ} value="" onChange={() => {}} />);
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining(`subject_id=${SUBJ}`)),
    );
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("level=topic"));
    expect(await screen.findByText("Reading Comprehension")).toBeInTheDocument();
  });

  test("MicrotopicSelect narrows to the chosen topic via parent_topic_id", async () => {
    render(<MicrotopicSelect topicId={TOPIC} value="" onChange={() => {}} />);
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining(`parent_topic_id=${TOPIC}`)),
    );
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("level=microtopic"));
  });

  test("ExamSelect filters by exam family; ExamPhaseSelect disabled until an exam is chosen", async () => {
    render(<ExamSelect familyId={FAM} value="" onChange={() => {}} />);
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining(`exam_family_id=${FAM}`)),
    );
    render(<ExamPhaseSelect examId="" value="" onChange={() => {}} />);
    expect(screen.getByTestId("select-exam-phase")).toBeDisabled();
  });
});

describe("assignment scope produces an exactly-one-scope payload", () => {
  const perms = { canProposeAssignment: true, canReviewAssignment: false };

  test("Global proposes is_global with no id column", async () => {
    render(<ExamAssignments perms={perms} promptIdParam={PROMPT} />);
    await screen.findByTestId("assignment-propose");
    fireEvent.change(screen.getByTestId("assignment-scope"), { target: { value: "global" } });
    fireEvent.change(screen.getByTestId("assignment-reason"), { target: { value: "route globally please" } });
    fireEvent.click(screen.getByTestId("assignment-propose-submit"));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const [, body] = api.post.mock.calls[0];
    expect(body.is_global).toBe(true);
    ["exam_family_id", "exam_id", "exam_phase_id"].forEach((k) => expect(body[k]).toBeUndefined());
  });

  test("Exam scope sends exam_id only (no family/phase leakage)", async () => {
    render(<ExamAssignments perms={perms} promptIdParam={PROMPT} />);
    await screen.findByTestId("assignment-propose");
    // scope defaults to exam_id; pick a family (filter) then the exam (leaf).
    fireEvent.change(screen.getByTestId("assignment-filter-family"), { target: { value: FAM } });
    await screen.findByText("SSC CGL");
    fireEvent.change(screen.getByTestId("assignment-scope-exam"), { target: { value: EXAM } });
    fireEvent.change(screen.getByTestId("assignment-reason"), { target: { value: "applies to SSC CGL" } });
    fireEvent.click(screen.getByTestId("assignment-propose-submit"));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const [, body] = api.post.mock.calls[0];
    expect(body.exam_id).toBe(EXAM);
    expect(body.is_global).toBeUndefined();
    expect(body.exam_family_id).toBeUndefined();
    expect(body.exam_phase_id).toBeUndefined();
  });
});

describe("readable labels in tables", () => {
  test("scopeLabel prefers resolved names over UUIDs", () => {
    expect(scopeLabel({ is_global: true })).toMatch(/Global/);
    expect(scopeLabel({ exam_id: EXAM, exam_name: "SSC CGL" })).toBe("Exam: SSC CGL");
    expect(scopeLabel({ exam_phase_id: PHASE, exam_phase_name: "Tier 1" })).toBe("Phase: Tier 1");
    expect(scopeLabel({ exam_family_id: FAM, exam_family_name: "SSC" })).toBe("Family: SSC");
  });

  test("assignment table renders the exam name, not the bare UUID", async () => {
    routeGet({
      targets: { items: [{ id: "t1", exam_id: EXAM, exam_name: "SSC CGL", applicability_status: "active", updated_at: "2026-07-03T00:00:00Z", priority_score: 5 }] },
    });
    render(<ExamAssignments perms={{ canProposeAssignment: true, canReviewAssignment: false }} promptIdParam={PROMPT} />);
    expect(await screen.findByText("Exam: SSC CGL")).toBeInTheDocument();
    expect(screen.queryByText(EXAM)).toBeNull();
  });
});

describe("needs_correction note is shown read-only to the author", () => {
  test("renders the reviewer note without any edit control", async () => {
    routeGet({ correctionNote: { note: { reviewer_notes: "Fix the tense in sentence 2.", reason: "grammar issues", actor_email: "rev@x.io", created_at: "2026-07-05T00:00:00Z" } } });
    render(<CorrectionNote promptId={PROMPT} />);
    expect(await screen.findByTestId("correction-note")).toBeInTheDocument();
    expect(screen.getByText(/Fix the tense in sentence 2\./)).toBeInTheDocument();
    // read-only: a note region, never a form control
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });

  test("renders nothing when there is no correction note", async () => {
    routeGet({ correctionNote: { note: null } });
    const { container } = render(<CorrectionNote promptId={PROMPT} />);
    await waitFor(() => expect(container.querySelector('[data-testid="correction-note"]')).toBeNull());
  });
});
