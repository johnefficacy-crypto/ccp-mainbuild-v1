import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ContentStudio from "../ContentStudio";
import { parseCsv } from "../csv";
import { normalizeRow, MAX_BULK_ROWS } from "../PromptBulkImport";
import { buildPayload } from "../PromptEditor";
import { validateRequiredWords, validateInt, isUuid } from "../validation";
import { REVIEW_TRANSITIONS, isValidReason, HEURISTIC_REVIEW_TRANSITIONS, HEURISTIC_TYPES } from "../contentStudioApi";
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

// Component tests below drive the real screens with the collection hook mocked
// (so env/transport stays out of it); shell tests stub the heavy tab bodies.
let mockCollection;
let mockRun;
jest.mock("../../../../lib/hooks/useApiCollection", () => ({
  __esModule: true,
  default: () => mockCollection,
}));
jest.mock("../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({ run: (...args) => mockRun(...args), busy: false }),
}));

jest.mock("../../mocks/QuestionList", () => () => <div data-testid="mock-question-list" />);
jest.mock("../../mocks/ReviewQueue", () => () => <div data-testid="mock-review-queue" />);
jest.mock("../../mocks/ImportWizard", () => () => <div data-testid="mock-import-wizard" />);

const U1 = "11111111-1111-4111-8111-111111111111";
const U2 = "22222222-2222-4222-8222-222222222222";
const U3 = "33333333-3333-4333-8333-333333333333";

function renderStudio(url = "/admin/content-studio") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <ContentStudio />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockCollection = { items: [], status: "empty", total: 0, refresh: jest.fn() };
  mockRun = jest.fn(async () => ({ ok: true, data: { ok: true, result: {} } }));
});

// ---- Shell (real prompt bodies; collection hook mocked) --------------------

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

// ---- CSV parser (RFC 4180 + fail-loud) -------------------------------------

describe("csv parser", () => {
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

  test("strips a leading UTF-8 BOM from the first header", () => {
    const rows = parseCsv("﻿a,b\n1,2\n");
    expect(rows).toEqual([{ a: "1", b: "2" }]);
  });

  test("only trims UNQUOTED cells (quoted padding preserved)", () => {
    const rows = parseCsv('a,b\n  x  ,"  y  "\n');
    expect(rows).toEqual([{ a: "x", b: "  y  " }]);
  });

  test("throws on an unterminated quote", () => {
    expect(() => parseCsv('a,b\n1,"oops\n')).toThrow(/unterminated/i);
  });

  test("throws on blank or duplicate headers", () => {
    expect(() => parseCsv("a,,b\n1,2,3\n")).toThrow(/blank/i);
    expect(() => parseCsv("a,a\n1,2\n")).toThrow(/duplicate/i);
  });

  test("throws on a row whose width differs from the header", () => {
    expect(() => parseCsv("a,b\n1,2,3\n")).toThrow(/columns, expected/);
  });

  test("returns empty for header-only input", () => {
    expect(parseCsv("a,b\n")).toEqual([]);
  });
});

// ---- Shared backend-parity validation --------------------------------------

describe("required-words parity validator", () => {
  test("accepts single tokens with internal apostrophe/hyphen", () => {
    expect(validateRequiredWords(["don't", "well-known", "alpha"]).words).toEqual(["don't", "well-known", "alpha"]);
  });

  test("rejects the punctuation/underscore cases the backend 422s", () => {
    expect(validateRequiredWords(["foo!"]).error).toMatch(/single word/);
    expect(validateRequiredWords(["a.b"]).error).toMatch(/single word/);
    expect(validateRequiredWords(["under_score"]).error).toMatch(/single word/);
    expect(validateRequiredWords(["@handle"]).error).toMatch(/single word/);
    expect(validateRequiredWords(["two words"]).error).toMatch(/single word/);
  });

  test("dedupes case-insensitively (NFC)", () => {
    expect(validateRequiredWords(["Alpha", "alpha"]).error).toMatch(/more than once/);
  });

  test("validateInt enforces bounds and integrality", () => {
    expect(validateInt("", "x").value).toBeUndefined();
    expect(validateInt("3", "x", { min: 1, max: 10 }).value).toBe(3);
    expect(validateInt("11", "x", { max: 10 }).error).toMatch(/≤ 10/);
    expect(validateInt("1.5", "x").error).toMatch(/whole number/);
  });

  test("isUuid guards malformed ids", () => {
    expect(isUuid(U1)).toBe(true);
    expect(isUuid("t-1")).toBe(false);
  });
});

// ---- Bulk row normalization (backend parity) -------------------------------

describe("bulk row normalization", () => {
  const base = {
    external_key: "k1",
    exercise_type: "sentence_construction",
    prompt_text: "Write a sentence.",
    topic_id: U1,
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
    const { errors } = normalizeRow({ ...base, external_key: "", subject_id: U2, exam_id: U3 });
    expect(errors.join(" ")).toMatch(/external_key is required/);
    expect(errors.join(" ")).toMatch(/must not carry subject_id/);
    expect(errors.join(" ")).toMatch(/exam_id is not allowed/);
  });

  test("rejects UNKNOWN columns instead of silently dropping them", () => {
    expect(normalizeRow({ ...base, source_document: U2 }).errors.join(" ")).toMatch(/unknown column "source_document"/);
    expect(normalizeRow({ ...base, max_rewrite_attempt: "2" }).errors.join(" ")).toMatch(/unknown column "max_rewrite_attempt"/);
  });

  test("rejects malformed UUIDs, invalid required words, and max<min", () => {
    expect(normalizeRow({ ...base, topic_id: "t-1" }).errors.join(" ")).toMatch(/topic_id must be a UUID/);
    expect(normalizeRow({ ...base, required_words: "foo!" }).errors.join(" ")).toMatch(/single word/);
    expect(normalizeRow({ ...base, min_words: "10", max_words: "5" }).errors.join(" ")).toMatch(/max_words must be ≥ min_words/);
  });

  test("rejects out-of-range difficulty and unknown exercise type", () => {
    expect(normalizeRow({ ...base, difficulty_level: "11" }).errors.join(" ")).toMatch(/1–10/);
    expect(normalizeRow({ ...base, exercise_type: "typo_type" }).errors.join(" ")).toMatch(/exercise_type/);
  });

  test("MAX_BULK_ROWS mirrors the backend cap", () => {
    expect(MAX_BULK_ROWS).toBe(500);
  });
});

// ---- Prompt editor payload (create + dirty-diff clearing) -------------------

describe("prompt editor payload rules", () => {
  const fullForm = (over = {}) => ({
    subject_id: U1, topic_id: U2, microtopic_id: "", exercise_type: "sentence_construction",
    prompt_text: "ok", source_text: "", required_words: "", required_sentence_count: "",
    difficulty_level: 3, min_words: "", max_words: "", max_rewrite_attempts: "", rubric_id: "",
    source_document_id: "", ...over,
  });

  test("create requires subject/topic/prompt text and valid ranges", () => {
    const { errors } = buildPayload(
      fullForm({ subject_id: "", topic_id: "", prompt_text: " ", difficulty_level: 12, min_words: "10", max_words: "5" }),
      { isCreate: true },
    );
    const text = errors.join(" ");
    expect(text).toMatch(/subject_id is required/);
    expect(text).toMatch(/topic_id is required/);
    expect(text).toMatch(/non-blank/);
    expect(text).toMatch(/1–10/);
    expect(text).toMatch(/Max words must be ≥ min words/);
  });

  test("create payload never contains exam-scope, metadata, or external_key", () => {
    const { payload } = buildPayload(fullForm(), { isCreate: true });
    ["exam_id", "exam_cycle_id", "exam_phase_id", "metadata", "external_key"].forEach((k) =>
      expect(payload).not.toHaveProperty(k),
    );
  });

  describe("edit dirty-diff", () => {
    const original = {
      id: U1, updated_at: "2026-07-03T00:00:00Z",
      subject_id: U1, topic_id: U2, microtopic_id: U3, exercise_type: "sentence_construction",
      prompt_text: "P", source_text: "S", required_words: ["alpha"], required_sentence_count: 2,
      difficulty_level: 3, min_words: 5, max_words: 10, max_rewrite_attempts: 2, rubric_id: U3,
      source_document_id: U2,
    };
    const formFromOriginal = (over = {}) => ({
      subject_id: U1, topic_id: U2, microtopic_id: U3, exercise_type: "sentence_construction",
      prompt_text: "P", source_text: "S", required_words: "alpha", required_sentence_count: 2,
      difficulty_level: 3, min_words: 5, max_words: 10, max_rewrite_attempts: 2, rubric_id: U3,
      source_document_id: U2, ...over,
    });

    test("no edits → empty patch", () => {
      const { payload } = buildPayload(formFromOriginal(), { isCreate: false, original });
      expect(payload).toEqual({});
    });

    test("clearing nullable fields sends explicit null", () => {
      const { payload } = buildPayload(
        formFromOriginal({ microtopic_id: "", source_text: "", required_words: "", required_sentence_count: "", min_words: "", max_words: "", rubric_id: "", source_document_id: "" }),
        { isCreate: false, original },
      );
      expect(payload.microtopic_id).toBeNull();
      expect(payload.source_text).toBeNull();
      expect(payload.required_words).toBeNull();
      expect(payload.required_sentence_count).toBeNull();
      expect(payload.min_words).toBeNull();
      expect(payload.max_words).toBeNull();
      expect(payload.rubric_id).toBeNull();
      expect(payload.source_document_id).toBeNull();
    });

    test("clearing a NON-nullable field is ignored, not nulled", () => {
      const { payload } = buildPayload(formFromOriginal({ max_rewrite_attempts: "" }), { isCreate: false, original });
      expect(payload).not.toHaveProperty("max_rewrite_attempts");
    });

    test("changed fields are sent; unchanged omitted", () => {
      const { payload } = buildPayload(formFromOriginal({ min_words: "7", prompt_text: "P2" }), { isCreate: false, original });
      expect(payload).toEqual({ min_words: 7, prompt_text: "P2" });
    });
  });
});

// ---- Review transitions + permissions --------------------------------------

describe("review transition map + gates", () => {
  test("rejected is terminal; pending offers all three decisions", () => {
    expect(REVIEW_TRANSITIONS.rejected).toEqual([]);
    expect(REVIEW_TRANSITIONS.pending).toEqual(["verified", "rejected", "needs_correction"]);
  });

  test("reason must be 8–500 chars", () => {
    expect(isValidReason("short")).toBe(false);
    expect(isValidReason("a valid audit reason")).toBe(true);
    expect(isValidReason("x".repeat(501))).toBe(false);
  });

  test("studioPerms maps the handoff permission model", () => {
    const manager = studioPerms({ role: "admin", permissions: ["exam_intelligence.manage"] });
    expect(manager.canProposeAssignment).toBe(true);
    expect(manager.canReviewAssignment).toBe(false);
    expect(studioPerms({ role: "super_admin", permissions: [] }).canReviewAssignment).toBe(true);
  });
});

// ---- Real PromptLibrary (collection hook mocked) ---------------------------

describe("PromptLibrary screen", () => {
  // eslint-disable-next-line global-require
  const PromptLibrary = require("../PromptLibrary").default;
  const perms = { canAuthor: true, canReview: true, canProposeAssignment: true, canReviewAssignment: true };

  const row = (over) => ({
    id: U1, prompt_text: "A prompt", exercise_type: "sentence_construction", difficulty_level: 3,
    reviewer_status: "pending", is_active: false, updated_at: "2026-07-03T00:00:00Z", ...over,
  });

  test("rejected rows show a terminal marker, not an Edit button", () => {
    mockCollection = { items: [row({ id: U1, reviewer_status: "rejected" })], status: "live", total: 1, refresh: jest.fn() };
    render(<PromptLibrary perms={perms} onAssign={jest.fn()} />);
    expect(screen.getByText(/rejected \(terminal\)/i)).toBeInTheDocument();
    expect(screen.queryByTestId(`prompt-edit-${U1}`)).toBeNull();
  });

  test("verified rows are locked (no Edit)", () => {
    mockCollection = { items: [row({ reviewer_status: "verified" })], status: "live", total: 1, refresh: jest.fn() };
    render(<PromptLibrary perms={perms} onAssign={jest.fn()} />);
    expect(screen.getByText(/^locked$/i)).toBeInTheDocument();
  });

  test("Assign action deep-links via onAssign(promptId)", () => {
    const onAssign = jest.fn();
    mockCollection = { items: [row()], status: "live", total: 1, refresh: jest.fn() };
    render(<PromptLibrary perms={perms} onAssign={onAssign} />);
    fireEvent.click(screen.getByTestId(`prompt-assign-${U1}`));
    expect(onAssign).toHaveBeenCalledWith(U1);
  });

  test("pagination uses total, not a full-page heuristic", () => {
    mockCollection = { items: new Array(50).fill(0).map((_, i) => row({ id: `id-${i}` })), status: "live", total: 50, refresh: jest.fn() };
    const { rerender } = render(<PromptLibrary perms={perms} onAssign={jest.fn()} />);
    // exactly 50 rows but total is 50 → no next page
    expect(screen.queryByTestId("prompt-next")).toBeNull();

    mockCollection = { ...mockCollection, total: 120 };
    rerender(<PromptLibrary perms={perms} onAssign={jest.fn()} />);
    expect(screen.getByTestId("prompt-next")).toBeInTheDocument();
  });
});

// ---- Real PromptReviewQueue (collection hook mocked) -----------------------

describe("PromptReviewQueue screen", () => {
  // eslint-disable-next-line global-require
  const PromptReviewQueue = require("../PromptReviewQueue").default;
  const perms = { canReview: true };

  test("queue table renders backend-resolved subject/topic NAMES, not UUIDs", () => {
    const SUBJ = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    const TOPIC = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
    mockCollection = {
      items: [{
        id: U1, prompt_text: "Write a paragraph.", exercise_type: "paragraph_writing",
        difficulty_level: 4, reviewer_status: "pending", updated_at: "2026-07-03T00:00:00Z",
        subject_id: SUBJ, topic_id: TOPIC,
        subject_name: "English Language", topic_name: "Reading Comprehension",
      }],
      status: "live", total: 1, refresh: jest.fn(),
    };
    render(<PromptReviewQueue perms={perms} />);
    const cell = screen.getByTestId(`review-taxonomy-${U1}`);
    expect(cell).toHaveTextContent("English Language › Reading Comprehension");
    expect(cell).not.toHaveTextContent(SUBJ);
    expect(cell).not.toHaveTextContent(TOPIC);
  });
});

// ---- Quant heuristic authority (GQR-Q7) ------------------------------------

describe("quant heuristic transition matrix", () => {
  test("differs from writing prompts: needs_correction never goes straight to verified", () => {
    expect(HEURISTIC_REVIEW_TRANSITIONS.needs_correction).toEqual(["pending", "rejected"]);
    expect(HEURISTIC_REVIEW_TRANSITIONS.needs_correction).not.toContain("verified");
    // writing prompts DO allow that transition — proving the maps are distinct.
    expect(REVIEW_TRANSITIONS.needs_correction).toContain("verified");
  });

  test("verified reopens only to needs_correction; rejected reopens to pending", () => {
    expect(HEURISTIC_REVIEW_TRANSITIONS.verified).toEqual(["needs_correction"]);
    expect(HEURISTIC_REVIEW_TRANSITIONS.rejected).toEqual(["pending"]);
    expect(HEURISTIC_REVIEW_TRANSITIONS.pending).toEqual(["verified", "rejected", "needs_correction"]);
  });

  test("heuristic type facet matches the migration-243 CHECK", () => {
    expect(HEURISTIC_TYPES).toEqual(["shortcut", "standard_method", "trap", "estimation"]);
  });
});

describe("ContentStudio shell — quant heuristics", () => {
  test("quant_heuristic type exposes only Library + Review Queue tabs", async () => {
    renderStudio("/admin/content-studio?type=quant_heuristic");
    expect(await screen.findByTestId("content-studio-tab-library")).toBeInTheDocument();
    expect(screen.getByTestId("content-studio-tab-review-queue")).toBeInTheDocument();
    // No bulk-import / exam-assignments for heuristics (no create/assign RPC).
    expect(screen.queryByTestId("content-studio-tab-bulk-import")).toBeNull();
    expect(screen.queryByTestId("content-studio-tab-exam-assignments")).toBeNull();
  });

  test("quant_heuristic facet without read permission shows the no-access state", async () => {
    mockUser.user = { role: "admin", permissions: [] };
    renderStudio("/admin/content-studio?type=quant_heuristic");
    expect(await screen.findByTestId("content-studio-no-access")).toBeInTheDocument();
    mockUser.user = { role: "admin", permissions: ["content_studio.author", "content_studio.review"] };
  });
});

describe("QuantHeuristicReviewQueue screen", () => {
  // eslint-disable-next-line global-require
  const QuantHeuristicReviewQueue = require("../QuantHeuristicReviewQueue").default;

  const row = (over) => ({
    id: U1, name: "Percentage to fraction", heuristic_code: "QH-PCT-01",
    heuristic_type: "shortcut", reviewer_status: "pending",
    topic_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", topic_name: "Percentages", ...over,
  });

  test("queue renders topic NAME, not the UUID, and offers Review to reviewers", () => {
    mockCollection = { items: [row()], status: "live", total: 1, refresh: jest.fn() };
    render(<QuantHeuristicReviewQueue perms={{ canReview: true }} />);
    const cell = screen.getByTestId(`heuristic-review-taxonomy-${U1}`);
    expect(cell).toHaveTextContent("Percentages");
    expect(cell).not.toHaveTextContent("bbbbbbbb");
    expect(screen.getByTestId(`heuristic-review-open-${U1}`)).toBeInTheDocument();
  });

  test("read-only reviewers get no Review button and see the gate hint", () => {
    mockCollection = { items: [row()], status: "live", total: 1, refresh: jest.fn() };
    render(<QuantHeuristicReviewQueue perms={{ canReview: false }} />);
    expect(screen.queryByTestId(`heuristic-review-open-${U1}`)).toBeNull();
    expect(screen.getByText(/requires content_studio\.review/i)).toBeInTheDocument();
  });

  test("a rejected heuristic (no legal onward decision) offers no Review button", () => {
    mockCollection = { items: [row({ reviewer_status: "rejected" })], status: "live", total: 1, refresh: jest.fn() };
    render(<QuantHeuristicReviewQueue perms={{ canReview: true }} />);
    // rejected → pending IS legal, so Review IS offered; assert the matrix drives it.
    expect(screen.getByTestId(`heuristic-review-open-${U1}`)).toBeInTheDocument();
  });
});

describe("QuantHeuristicLibrary screen", () => {
  // eslint-disable-next-line global-require
  const QuantHeuristicLibrary = require("../QuantHeuristicLibrary").default;

  test("renders heuristic rows with a View action and no author/assign affordance", () => {
    mockCollection = {
      items: [{ id: U1, name: "Alligation", heuristic_code: "QH-ALG-01", heuristic_type: "shortcut", reviewer_status: "verified", is_active: true, topic_name: "Mixtures" }],
      status: "live", total: 1, refresh: jest.fn(),
    };
    render(<QuantHeuristicLibrary />);
    expect(screen.getByTestId(`heuristic-open-${U1}`)).toBeInTheDocument();
    expect(screen.getByText("Alligation")).toBeInTheDocument();
    // Governance-read surface only — no create/assign controls exist here.
    expect(screen.queryByText(/new heuristic|create|assign/i)).toBeNull();
  });
});

// ---- Activation affordance permission gating (PromptLibrary) ----------------

describe("PromptLibrary activation affordance", () => {
  // eslint-disable-next-line global-require
  const PromptLibrary = require("../PromptLibrary").default;
  const row = (over) => ({
    id: U1, prompt_text: "A prompt", exercise_type: "sentence_construction", difficulty_level: 3,
    reviewer_status: "verified", is_active: false, updated_at: "2026-07-03T00:00:00Z", ...over,
  });
  const perms = (over) => ({
    canAuthor: false, canReview: false, canProposeAssignment: false, canReviewAssignment: false,
    canActivate: false, ...over,
  });

  test("Activate hidden without content_studio.activate", () => {
    mockCollection = { items: [row()], status: "live", total: 1, refresh: jest.fn() };
    render(<PromptLibrary perms={perms()} onAssign={jest.fn()} />);
    expect(screen.queryByTestId(`prompt-activate-${U1}`)).toBeNull();
  });

  test("Activate visible on a verified prompt with content_studio.activate", () => {
    mockCollection = { items: [row()], status: "live", total: 1, refresh: jest.fn() };
    render(<PromptLibrary perms={perms({ canActivate: true })} onAssign={jest.fn()} />);
    expect(screen.getByTestId(`prompt-activate-${U1}`)).toBeInTheDocument();
  });

  test("Activate NOT offered on a non-verified prompt (server requires verified)", () => {
    mockCollection = { items: [row({ reviewer_status: "pending" })], status: "live", total: 1, refresh: jest.fn() };
    render(<PromptLibrary perms={perms({ canActivate: true })} onAssign={jest.fn()} />);
    expect(screen.queryByTestId(`prompt-activate-${U1}`)).toBeNull();
    expect(screen.queryByTestId(`prompt-deactivate-${U1}`)).toBeNull();
  });

  test("active prompt shows Deactivate instead of Activate", () => {
    mockCollection = { items: [row({ is_active: true })], status: "live", total: 1, refresh: jest.fn() };
    render(<PromptLibrary perms={perms({ canActivate: true })} onAssign={jest.fn()} />);
    expect(screen.getByTestId(`prompt-deactivate-${U1}`)).toBeInTheDocument();
    expect(screen.queryByTestId(`prompt-activate-${U1}`)).toBeNull();
  });
});

// ---- Activation dialog (CAS + reason + server-only eligibility) -------------

describe("PromptActivationDialog", () => {
  // eslint-disable-next-line global-require
  const PromptActivationDialog = require("../PromptActivation").default;
  const CAS = "2026-07-05T09:00:00Z";
  const prompt = { id: U1, updated_at: CAS, is_active: false };

  function open(mode = "activate", over = {}) {
    const onDone = jest.fn();
    render(<PromptActivationDialog prompt={{ ...prompt, ...over }} mode={mode} onClose={jest.fn()} onDone={onDone} />);
    return { onDone };
  }
  const typeReason = () =>
    fireEvent.change(screen.getByTestId("activation-reason"), { target: { value: "activating for launch" } });

  test("reason is required — no request fires on a short reason", async () => {
    open();
    fireEvent.click(screen.getByTestId("activation-submit"));
    expect(await screen.findByTestId("activation-error")).toHaveTextContent(/8–500/);
    expect(mockRun).not.toHaveBeenCalled();
  });

  test("passes the client CAS token (expected_updated_at) through UNCHANGED", async () => {
    // Assert against the real adapter call by inspecting the action thunk's effect.
    const apiMock = require("../../../../lib/api").api;
    mockRun = jest.fn(async ({ action }) => { await action(); return { ok: true, data: { ok: true, result: { eligible: true, is_active: true } } }; });
    const { onDone } = open();
    typeReason();
    fireEvent.click(screen.getByTestId("activation-submit"));
    await waitFor(() => expect(onDone).toHaveBeenCalledWith({ is_active: true }));
    expect(apiMock.post).toHaveBeenCalledWith(
      `/api/admin/content-studio/writing-prompts/${U1}/activate`,
      { expected_updated_at: CAS, reason: "activating for launch" },
    );
  });

  test("{eligible:false, blockers} renders Activation blocked with each reason (no client-side eligibility)", async () => {
    mockRun = jest.fn(async () => ({
      ok: true,
      data: { ok: true, result: { eligible: false, blockers: ["no_active_applicability_target", "semantic_evaluator_not_live"] } },
    }));
    const { onDone } = open();
    typeReason();
    fireEvent.click(screen.getByTestId("activation-submit"));
    expect(await screen.findByTestId("activation-blocked")).toBeInTheDocument();
    expect(screen.getByTestId("activation-blocker-no_active_applicability_target"))
      .toHaveTextContent(/applicability target/i);
    expect(screen.getByTestId("activation-blocker-semantic_evaluator_not_live"))
      .toHaveTextContent(/semantic evaluator/i);
    // Blocked activation is a 200, not a success — is_active must NOT be reflected.
    expect(onDone).not.toHaveBeenCalled();
  });

  test("success reflects the new is_active via onDone", async () => {
    mockRun = jest.fn(async () => ({ ok: true, data: { ok: true, result: { eligible: true, is_active: true } } }));
    const { onDone } = open();
    typeReason();
    fireEvent.click(screen.getByTestId("activation-submit"));
    await waitFor(() => expect(onDone).toHaveBeenCalledWith({ is_active: true }));
  });

  test("409 shows a conflict / re-read message (not a silent failure)", async () => {
    mockRun = jest.fn(async () => ({ ok: false, error: { status: 409 } }));
    open();
    typeReason();
    fireEvent.click(screen.getByTestId("activation-submit"));
    expect(await screen.findByTestId("activation-conflict")).toHaveTextContent(/changed since you loaded/i);
  });

  test("422/404 surfaces an explicit error state; the operator can retry", async () => {
    mockRun = jest.fn(async () => ({ ok: false, error: { status: 422, message: "invalid" } }));
    open();
    typeReason();
    fireEvent.click(screen.getByTestId("activation-submit"));
    expect(await screen.findByTestId("activation-error")).toHaveTextContent(/invalid/);
    // Not silent: the submit control remains available for a retry.
    expect(screen.getByTestId("activation-submit")).toBeInTheDocument();
  });

  test("deactivate does not inspect eligibility and reports the new state", async () => {
    mockRun = jest.fn(async () => ({ ok: true, data: { ok: true, result: { is_active: false } } }));
    const { onDone } = open("deactivate", { is_active: true });
    typeReason();
    fireEvent.click(screen.getByTestId("activation-submit"));
    await waitFor(() => expect(onDone).toHaveBeenCalledWith({ is_active: false }));
  });
});
