import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ContentStudio from "../ContentStudio";
import { parseCsv } from "../csv";
import { normalizeRow } from "../PromptBulkImport";
import { parseRequiredWords, buildPayload } from "../PromptEditor";
import { REVIEW_TRANSITIONS, isValidReason } from "../contentStudioApi";
import { studioPerms } from "../permissions";

const mockUser = { user: { role: "admin", permissions: ["content_studio.author", "content_studio.review"] } };
jest.mock("../../../../lib/authContext", () => ({
  useAuth: () => mockUser,
}));

// env.js throws without REACT_APP_BACKEND_URL; the adapter is exercised via its
// exported pure helpers, so stub the transport layer.
jest.mock("../../../../lib/api", () => ({
  api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() },
  getApiErrorMessage: (e) => e?.message || "error",
}));

// The lazy tab bodies fetch; stub the heavy ones so shell tests stay unit-level.
jest.mock("../../mocks/QuestionList", () => () => <div data-testid="mock-question-list" />);
jest.mock("../../mocks/ReviewQueue", () => () => <div data-testid="mock-review-queue" />);
jest.mock("../../mocks/ImportWizard", () => () => <div data-testid="mock-import-wizard" />);
jest.mock("../PromptLibrary", () => () => <div data-testid="prompt-library" />);
jest.mock("../PromptReviewQueue", () => () => <div data-testid="prompt-review-queue" />);
jest.mock("../PromptBulkImport", () => ({
  __esModule: true,
  ...jest.requireActual("../PromptBulkImport"),
  default: () => {
    const ReactActual = jest.requireActual("react");
    return ReactActual.createElement("div", { "data-testid": "prompt-bulk-import" });
  },
}));
jest.mock("../ExamAssignments", () => () => <div data-testid="exam-assignments" />);

function renderStudio(url = "/admin/content-studio") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <ContentStudio />
    </MemoryRouter>,
  );
}

describe("ContentStudio shell", () => {
  test("defaults to library tab, objective_question type (redirect-faithful)", async () => {
    renderStudio();
    expect(await screen.findByTestId("mock-question-list")).toBeInTheDocument();
    expect(screen.getByTestId("content-studio-tab-library").getAttribute("aria-selected")).toBe("true");
  });

  test("tab query param selects the tab", async () => {
    renderStudio("/admin/content-studio?tab=review-queue");
    expect(await screen.findByTestId("mock-review-queue")).toBeInTheDocument();
  });

  test("writing_prompt facet renders the prompt library", async () => {
    renderStudio("/admin/content-studio?tab=library&type=writing_prompt");
    expect(await screen.findByTestId("prompt-library")).toBeInTheDocument();
  });

  test("exam-assignments tab exists only for writing prompts", async () => {
    renderStudio("/admin/content-studio?tab=exam-assignments&type=writing_prompt");
    expect(await screen.findByTestId("exam-assignments")).toBeInTheDocument();
    renderStudio("/admin/content-studio?tab=exam-assignments&type=objective_question");
    // falls back to library for objective questions
    expect(await screen.findByTestId("mock-question-list")).toBeInTheDocument();
  });

  test("switching content type updates the facet", async () => {
    renderStudio("/admin/content-studio?tab=bulk-import&type=writing_prompt");
    expect(await screen.findByTestId("prompt-bulk-import")).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("content-studio-type"), { target: { value: "objective_question" } });
    expect(await screen.findByTestId("mock-import-wizard")).toBeInTheDocument();
  });

  test("no activate/publish affordance is rendered anywhere in the shell", () => {
    renderStudio("/admin/content-studio?type=writing_prompt");
    expect(screen.queryByText(/activate prompt|publish live/i)).toBeNull();
  });

  test("writing_prompt facet without read permission shows the no-access state", async () => {
    mockUser.user = { role: "admin", permissions: [] };
    renderStudio("/admin/content-studio?type=writing_prompt");
    expect(await screen.findByTestId("content-studio-no-access")).toBeInTheDocument();
    mockUser.user = { role: "admin", permissions: ["content_studio.author", "content_studio.review"] };
  });
});

describe("csv parser (RFC 4180)", () => {
  test("handles quoted commas and escaped quotes", () => {
    const rows = parseCsv('external_key,prompt_text\nk1,"Write, with commas"\nk2,"He said ""hi"""\n');
    expect(rows).toEqual([
      { external_key: "k1", prompt_text: "Write, with commas" },
      { external_key: "k2", prompt_text: 'He said "hi"' },
    ]);
  });

  test("handles CRLF and skips blank lines", () => {
    const rows = parseCsv("a,b\r\n1,2\r\n\r\n3,4\r\n");
    expect(rows).toEqual([{ a: "1", b: "2" }, { a: "3", b: "4" }]);
  });

  test("returns empty for header-only input", () => {
    expect(parseCsv("a,b\n")).toEqual([]);
  });
});

describe("bulk row normalization", () => {
  const base = {
    external_key: "k1",
    exercise_type: "sentence_construction",
    prompt_text: "Write a sentence.",
    topic_id: "t-1",
    difficulty_level: "3",
  };

  test("valid row passes and coerces ints", () => {
    const { row, errors } = normalizeRow({ ...base, min_words: "5", required_words: "alpha|beta" });
    expect(errors).toEqual([]);
    expect(row.difficulty_level).toBe(3);
    expect(row.min_words).toBe(5);
    expect(row.required_words).toEqual(["alpha", "beta"]);
  });

  test("rejects missing external_key and per-row subject_id / exam ids", () => {
    const { errors } = normalizeRow({ ...base, external_key: "", subject_id: "s-1", exam_id: "e-1" });
    expect(errors.join(" ")).toMatch(/external_key is required/);
    expect(errors.join(" ")).toMatch(/must not carry subject_id/);
    expect(errors.join(" ")).toMatch(/exam_id is not allowed/);
  });

  test("rejects out-of-range difficulty and unknown exercise type", () => {
    expect(normalizeRow({ ...base, difficulty_level: "11" }).errors.join(" ")).toMatch(/1–10/);
    expect(normalizeRow({ ...base, exercise_type: "typo_type" }).errors.join(" ")).toMatch(/exercise_type/);
  });
});

describe("prompt editor payload rules", () => {
  test("required_words must be single unique tokens", () => {
    expect(parseRequiredWords("alpha, beta").words).toEqual(["alpha", "beta"]);
    expect(parseRequiredWords("two words").error).toMatch(/single word/);
    expect(parseRequiredWords("Alpha, alpha").error).toMatch(/more than once/);
  });

  test("create requires subject/topic/prompt text and valid ranges", () => {
    const { errors } = buildPayload(
      { subject_id: "", topic_id: "", microtopic_id: "", exercise_type: "sentence_construction", prompt_text: " ", source_text: "", required_words: "", required_sentence_count: "", difficulty_level: 12, min_words: "10", max_words: "5", max_rewrite_attempts: "", rubric_id: "", source_document_id: "" },
      { isCreate: true },
    );
    const text = errors.join(" ");
    expect(text).toMatch(/subject_id is required/);
    expect(text).toMatch(/topic_id is required/);
    expect(text).toMatch(/non-blank/);
    expect(text).toMatch(/1–10/);
    expect(text).toMatch(/Max words must be ≥ min words/);
  });

  test("payload never contains exam-scope or external_key fields", () => {
    const { payload } = buildPayload(
      { subject_id: "s", topic_id: "t", microtopic_id: "", exercise_type: "sentence_construction", prompt_text: "ok", source_text: "", required_words: "", required_sentence_count: "", difficulty_level: 3, min_words: "", max_words: "", max_rewrite_attempts: "", rubric_id: "", source_document_id: "" },
      { isCreate: true },
    );
    expect(payload).not.toHaveProperty("exam_id");
    expect(payload).not.toHaveProperty("exam_cycle_id");
    expect(payload).not.toHaveProperty("exam_phase_id");
    expect(payload).not.toHaveProperty("metadata");
  });
});

describe("review transition map", () => {
  test("rejected is terminal; pending offers all three decisions", () => {
    expect(REVIEW_TRANSITIONS.rejected).toEqual([]);
    expect(REVIEW_TRANSITIONS.pending).toEqual(["verified", "rejected", "needs_correction"]);
    expect(REVIEW_TRANSITIONS.verified).toEqual(["rejected", "needs_correction"]);
  });
});

describe("permissions + reason gates", () => {
  test("reason must be 8–500 chars", () => {
    expect(isValidReason("short")).toBe(false);
    expect(isValidReason("a valid audit reason")).toBe(true);
    expect(isValidReason("x".repeat(501))).toBe(false);
  });

  test("studioPerms maps the handoff permission model", () => {
    const reviewer = studioPerms({ role: "admin", permissions: ["content_studio.review"] });
    expect(reviewer.canRead).toBe(true);
    expect(reviewer.canReview).toBe(true);
    expect(reviewer.canAuthor).toBe(false);
    const manager = studioPerms({ role: "admin", permissions: ["exam_intelligence.manage"] });
    expect(manager.canRead).toBe(true);
    expect(manager.canProposeAssignment).toBe(true);
    expect(manager.canReviewAssignment).toBe(false);
    const superAdmin = studioPerms({ role: "super_admin", permissions: [] });
    expect(superAdmin.canAuthor).toBe(true);
    expect(superAdmin.canReviewAssignment).toBe(true);
  });
});
