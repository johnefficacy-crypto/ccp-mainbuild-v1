/**
 * Answer structure review queue: filters, full edit form, edit-then-approve,
 * reject-needs-note, regenerate, and the reviewer-facing risk flags.
 */
import React from "react";
import { fireEvent, render, screen, waitFor, act } from "@testing-library/react";

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockPatch = jest.fn();
jest.mock("../../../../lib/api", () => ({
  api: {
    get: (...a) => mockGet(...a),
    post: (...a) => mockPost(...a),
    patch: (...a) => mockPatch(...a),
  },
  getApiErrorMessage: (e) => e?.message || "error",
}));

let mockCollection;
let mockCollectionParams;
jest.mock("../../../../lib/hooks/useApiCollection", () => ({
  __esModule: true,
  default: (_url, _seed, opts) => {
    mockCollectionParams = opts?.params;
    return mockCollection;
  },
}));
jest.mock("../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({
    run: async ({ action, onSuccess }) => {
      try {
        const data = await action();
        if (onSuccess) onSuccess(data);
        return { ok: true, data };
      } catch (error) {
        return { ok: false, error };
      }
    },
    busy: false,
  }),
}));

// eslint-disable-next-line import/first
import AnswerStructureReviewQueue, { formPatch, toForm } from "../AnswerStructureReviewQueue";

const SID = "00000000-0000-4000-8000-00000000a501";
const TOKEN = "2026-09-20T00:00:00Z";
const STRUCTURE = {
  id: SID,
  pyq_question_id: "q1",
  version: 1,
  status: "draft",
  directive: "Critically examine",
  demand: "Weigh both sides.",
  intro_angles: ["Define the office."],
  body_points: [
    { id: "p1", point: "Constitutional position", why: "Basis", evidence_type: "Articles", example: null, thinker: null, sub_points: [] },
    { id: "p2", point: "Friction points", why: null, evidence_type: null, example: null, thinker: null, sub_points: ["Delays"] },
  ],
  dimensions: ["Federal"],
  examples: [],
  conclusion_angles: ["Balanced verdict."],
  pitfalls: ["Only criticism."],
  word_budget: { total: 250, intro: 40, body: 170, conclusion: 40, basis: "word_limit" },
  sources_note: null,
  generated_by: "ai:claude-opus-5",
  generation_meta: {
    model: "claude-opus-5", prompt_version: "answer-structure-v1", attempts: 1, cost_usd: 0.05,
    uncertainty: ["Unsure the 2023 judgment is expected."],
    lint_warnings: [{ field: "body_points[0].example", kind: "named_case", match: "Bommai v. Union" }],
  },
  updated_at: TOKEN,
};

function detail(over = {}) {
  return {
    structure: { ...STRUCTURE, ...over },
    question: { text: "Critically examine the role of the Governor.", subject: "General Studies", paper: "GS2", year: 2023, marks: 15, word_limit: 250 },
    versions: [{ id: SID, version: 1, status: over.status || "draft" }],
    audit: [{ id: "au1", action: "answer_structure_draft_created", created_at: TOKEN, notes: "batch" }],
    allowed_transitions: ["in_review", "verified", "rejected"],
    editable: (over.status || "draft") === "draft" || over.status === "in_review",
  };
}

beforeEach(() => {
  mockGet.mockReset();
  mockPost.mockReset();
  mockPatch.mockReset();
  mockCollection = {
    items: [{ id: SID, version: 1, status: "draft", directive: "Critically examine",
      question: { excerpt: "Critically examine the role of the Governor…", subject: "General Studies", paper: "GS2", year: 2023 } }],
    status: "live", total: 1, refresh: jest.fn(),
  };
  mockGet.mockImplementation((url) => {
    if (url.includes("limit=1")) {
      return Promise.resolve({ facets: { subjects: ["General Studies"], papers: ["GS2", "GS3"], years: [2023, 2022] } });
    }
    return Promise.resolve(detail());
  });
});

const PERMS = { canReview: true, canAuthor: true };

async function openDialog() {
  render(<AnswerStructureReviewQueue perms={PERMS} />);
  fireEvent.click(screen.getByTestId(`structure-open-${SID}`));
  await screen.findByTestId("structure-review-dialog");
  await screen.findByTestId("structure-demand");
}

test("queue lists rows and filters by status, subject, paper and year", async () => {
  render(<AnswerStructureReviewQueue perms={PERMS} />);
  expect(screen.getAllByTestId("structure-queue-row")).toHaveLength(1);
  await waitFor(() => expect(screen.getByTestId("structure-filter-paper")).toHaveTextContent("GS3"));
  fireEvent.change(screen.getByTestId("structure-filter-paper"), { target: { value: "GS2" } });
  fireEvent.change(screen.getByTestId("structure-filter-year"), { target: { value: "2023" } });
  fireEvent.change(screen.getByTestId("structure-filter-status"), { target: { value: "in_review" } });
  fireEvent.change(screen.getByTestId("structure-filter-subject"), { target: { value: "General Studies" } });
  expect(mockCollectionParams).toMatchObject({ paper: "GS2", year: "2023", status: "in_review", subject: "General Studies", offset: 0 });
});

test("dialog shows the question, every field, the risk flags and the audit trail", async () => {
  await openDialog();
  expect(screen.getByTestId("structure-question")).toHaveTextContent("role of the Governor");
  expect(screen.getByTestId("structure-directive")).toHaveValue("Critically examine");
  expect(screen.getByTestId("structure-pitfalls")).toHaveValue("Only criticism.");
  expect(screen.getByTestId("structure-point-1-text")).toHaveValue("Friction points");
  expect(screen.getByTestId("structure-flags")).toHaveTextContent("Model unsure");
  expect(screen.getByTestId("structure-flags")).toHaveTextContent("Bommai v. Union");
  expect(screen.getByTestId("structure-audit")).toHaveTextContent("answer structure draft created");
});

test("edit-then-approve saves the edit first, then approves the NEW revision", async () => {
  mockPatch.mockResolvedValue({ ok: true, result: { updated_at: "2026-09-21T00:00:00Z" } });
  mockPost.mockResolvedValue({ ok: true });
  await openDialog();
  fireEvent.change(screen.getByTestId("structure-demand"), { target: { value: "A sharper demand." } });
  fireEvent.change(screen.getByTestId("structure-reason"), { target: { value: "tightened the demand" } });
  expect(screen.getByTestId("structure-decide-verified")).toHaveTextContent("Save & approve");
  await act(async () => { fireEvent.click(screen.getByTestId("structure-decide-verified")); });
  expect(mockPatch).toHaveBeenCalledWith(`/api/admin/content-studio/answer-structures/${SID}`, {
    expected_updated_at: TOKEN,
    reason: "tightened the demand",
    payload: { demand: "A sharper demand." },
  });
  expect(mockPost).toHaveBeenCalledWith(`/api/admin/content-studio/answer-structures/${SID}/review`, {
    status: "verified",
    expected_status: "draft",
    expected_updated_at: "2026-09-21T00:00:00Z",
  });
  expect(mockCollection.refresh).toHaveBeenCalled();
});

test("approve without edits sends the loaded CAS token", async () => {
  mockPost.mockResolvedValue({ ok: true });
  await openDialog();
  await act(async () => { fireEvent.click(screen.getByTestId("structure-decide-verified")); });
  expect(mockPatch).not.toHaveBeenCalled();
  expect(mockPost.mock.calls[0][1]).toMatchObject({ expected_updated_at: TOKEN, status: "verified" });
});

test("reject requires a note", async () => {
  mockPost.mockResolvedValue({ ok: true });
  await openDialog();
  await act(async () => { fireEvent.click(screen.getByTestId("structure-decide-rejected")); });
  expect(screen.getByRole("alert")).toHaveTextContent("needs a note");
  expect(mockPost).not.toHaveBeenCalled();
  fireEvent.change(screen.getByTestId("structure-notes"), { target: { value: "Invents a committee." } });
  await act(async () => { fireEvent.click(screen.getByTestId("structure-decide-rejected")); });
  expect(mockPost.mock.calls[0][1]).toMatchObject({ status: "rejected", review_notes: "Invents a committee." });
});

test("a 409 tells the reviewer to reload rather than deciding blind", async () => {
  mockPost.mockRejectedValue({ status: 409, message: "changed" });
  await openDialog();
  await act(async () => { fireEvent.click(screen.getByTestId("structure-decide-in_review")); });
  expect(screen.getByRole("alert")).toHaveTextContent("changed since you loaded it");
});

test("regenerate needs a reason and posts it", async () => {
  window.confirm = jest.fn(() => true);
  mockPost.mockResolvedValue({ ok: true });
  await openDialog();
  await act(async () => { fireEvent.click(screen.getByTestId("structure-regenerate")); });
  expect(mockPost).not.toHaveBeenCalled();
  fireEvent.change(screen.getByTestId("structure-reason"), { target: { value: "too generic, redo it" } });
  await act(async () => { fireEvent.click(screen.getByTestId("structure-regenerate")); });
  expect(mockPost).toHaveBeenCalledWith(`/api/admin/content-studio/answer-structures/${SID}/regenerate`, {
    reason: "too generic, redo it",
  });
});

test("a verified structure is read-only and can only be rejected", async () => {
  mockGet.mockImplementation((url) =>
    Promise.resolve(url.includes("limit=1") ? { facets: {} } : { ...detail({ status: "verified" }), editable: false }));
  await openDialog();
  expect(screen.getByTestId("structure-demand")).toBeDisabled();
  expect(screen.queryByTestId("structure-decide-verified")).toBeNull();
  expect(screen.getByTestId("structure-decide-rejected")).toBeInTheDocument();
});

test("formPatch sends only changed fields, lists as arrays, points as objects", () => {
  const form = toForm(STRUCTURE);
  expect(formPatch(STRUCTURE, form)).toEqual({});
  form.pitfalls = "One\n\nTwo  ";
  form.body_points = [...form.body_points, { id: "p3", point: "New", why: "", evidence_type: "", example: "", thinker: "", sub_points: "a\nb" }];
  const patch = formPatch(STRUCTURE, form);
  expect(patch.pitfalls).toEqual(["One", "Two"]);
  expect(patch.body_points[2]).toEqual({ id: "p3", point: "New", why: null, evidence_type: null, example: null, thinker: null, sub_points: ["a", "b"] });
  expect(Object.keys(patch).sort()).toEqual(["body_points", "pitfalls"]);
});
