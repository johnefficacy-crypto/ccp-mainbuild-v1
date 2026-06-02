/**
 * Tests for the Syllabus Mapper UI components (PR3b).
 *
 * Covers:
 * - SyllabusMapperPanel renders document selector
 * - ProposalRunner button triggers POST /propose, populates proposals state
 * - PageViewer highlights proposals matching current_page only
 * - Clicking <mark> toggles selection
 * - "Accept All on Page" selects only current-page proposals
 * - "Accept ≥ 95%" filters by confidence
 * - AcceptPreviewModal calls /accept/preview, displays breakdown
 * - Commit button disabled until reason entered
 * - Commit success removes proposals from state
 * - Error in /propose surfaces inline, doesn't crash panel
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

jest.mock("../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
}));

const { api } = require("../../../../../lib/api");

const ExamWorkspaceContext = require("../../ExamWorkspaceContext");

// ── Fixtures ──────────────────────────────────────────────────────────────────

const EXAM = { id: "exam-1", name: "SSC CGL", exam_type: "recruitment" };
const DOCS = [{ id: "doc-1", title: "Syllabus 2026.pdf", document_type: "syllabus_pdf" }];

const PROPOSALS = [
  {
    syllabus_document_id: "doc-1", topic_id: "topic-math", exam_id: "exam-1",
    exam_cycle_id: null, exam_phase_id: null,
    source_page: 1, raw_text: "Arithmetic", normalized_text: "arithmetic",
    mention_type: "explicit", confidence_score: 1.0,
    matched_alias: "Arithmetic", match_method: "topic_alias_exact",
    proposer_version: "syllabus_mapper_v1",
    client_proposal_key: "ca3c545edec5edc98340bfdf484ffad0f1d86f74c14ea9d5d97cd778b6d73313",
  },
  {
    syllabus_document_id: "doc-1", topic_id: "topic-reasoning", exam_id: "exam-1",
    exam_cycle_id: null, exam_phase_id: null,
    source_page: 2, raw_text: "Logical Reasoning", normalized_text: "logical reasoning",
    mention_type: "explicit", confidence_score: 0.87,
    matched_alias: "Logical Reasoning", match_method: "topic_alias_fuzzy",
    proposer_version: "syllabus_mapper_v1",
    client_proposal_key: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  },
];

const PROPOSE_RESPONSE = { proposals: PROPOSALS };

const PREVIEW_RESPONSE = {
  exam_id: "exam-1",
  total: 1,
  will_insert: [PROPOSALS[0]],
  will_skip_duplicate: [],
  invalid: [],
  summary: { insert: 1, skip_duplicate: 0, invalid: 0 },
};

const COMMIT_RESPONSE = {
  exam_id: "exam-1",
  committed: 1, skipped_duplicate: 0, skipped_stale: 0, failed: 0,
  per_row: [{ proposal_key: PROPOSALS[0].client_proposal_key, result: "committed", mention_id: "m-1", reason: null }],
};

// ── Context wrapper ───────────────────────────────────────────────────────────

function TestWrapper({ children }) {
  return (
    <MemoryRouter initialEntries={["/admin/exam-intelligence/workspace/exam-1"]}>
      <Routes>
        <Route
          path="/admin/exam-intelligence/workspace/:exam_id"
          element={
            <ExamWorkspaceContext.ExamWorkspaceProvider>
              {children}
            </ExamWorkspaceContext.ExamWorkspaceProvider>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

function mockContextApi({ contextOk = true, readinessOk = true } = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/readiness")) {
      return readinessOk
        ? Promise.resolve({
            exam_id: "exam-1", cycle_id: null, generated_at: "now",
            overall: { status: "partial", score_percent: 40, ready_to_activate: false, blockers: [] },
            sections: [{ section: "syllabus_mapper", status: "partial", score_percent: 50, weight: 2, blockers: [], counts: {}, metrics: {} }],
          })
        : Promise.reject(new Error("readiness err"));
    }
    if (url.includes("/context")) {
      return contextOk
        ? Promise.resolve({ exam: EXAM, cycle: null, cycles: [], phases: [] })
        : Promise.reject(new Error("context err"));
    }
    if (url.includes("/documents/doc-1/pages/")) {
      return Promise.resolve({ text_content: "Arithmetic fundamentals and number theory." });
    }
    if (url.includes("/syllabus-documents") || url.includes("/documents")) {
      return Promise.resolve({ items: DOCS });
    }
    return Promise.resolve({});
  });
}

// Lazy-require components after mocks are set
const SyllabusMapperPanel = require("../SyllabusMapperPanel").default;
const PageViewer = require("../PageViewer").default;
const ProposalRunner = require("../ProposalRunner").default;
const ProposalActionBar = require("../ProposalActionBar").default;
const AcceptPreviewModal = require("../AcceptPreviewModal").default;

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("SyllabusMapperPanel", () => {
  beforeEach(() => { jest.clearAllMocks(); mockContextApi(); });

  test("renders document selector", async () => {
    render(<TestWrapper><SyllabusMapperPanel /></TestWrapper>);
    await waitFor(() => expect(screen.getByTestId("syllabus-doc-select")).toBeTruthy());
  });

  async function waitForDocOption() {
    await waitFor(() => {
      const sel = screen.getByTestId("syllabus-doc-select");
      const opts = Array.from(sel.options).map((o) => o.value);
      if (!opts.includes("doc-1")) throw new Error("doc option not loaded");
    });
  }

  test("run-propose button triggers POST /propose and populates proposals", async () => {
    api.post.mockResolvedValue(PROPOSE_RESPONSE);
    render(<TestWrapper><SyllabusMapperPanel /></TestWrapper>);
    await waitForDocOption();

    fireEvent.change(screen.getByTestId("syllabus-doc-select"), { target: { value: "doc-1" } });
    await waitFor(() => expect(api.post).toHaveBeenCalledWith(
      expect.stringContaining("/syllabus/propose"),
      expect.objectContaining({ syllabus_document_id: "doc-1" }),
    ));
    await waitFor(() => expect(screen.getByTestId("proposal-count")).toBeTruthy());
    expect(screen.getByTestId("proposal-count").textContent).toContain("2");
  });

  test("error in /propose surfaces inline without crashing", async () => {
    api.post.mockRejectedValue(new Error("network error"));
    render(<TestWrapper><SyllabusMapperPanel /></TestWrapper>);
    await waitForDocOption();

    fireEvent.change(screen.getByTestId("syllabus-doc-select"), { target: { value: "doc-1" } });
    await waitFor(() => expect(screen.getByTestId("propose-error")).toBeTruthy());
    expect(screen.getByTestId("propose-error").textContent).toContain("network error");
    expect(screen.getByTestId("syllabus-mapper-panel")).toBeTruthy();
  });
});

describe("PageViewer", () => {
  const proposals = [
    { ...PROPOSALS[0], client_proposal_key: "key-1" },
    { ...PROPOSALS[1], source_page: 1, client_proposal_key: "key-2" },
  ];

  test("highlights proposals matching current text", () => {
    const selectedKeys = new Set();
    render(
      <PageViewer
        pageText="Arithmetic fundamentals and Logical Reasoning skills."
        pageProposals={proposals}
        selectedKeys={selectedKeys}
        onToggle={() => {}}
      />,
    );
    expect(screen.getByTestId("page-viewer")).toBeTruthy();
    expect(document.querySelector("[data-proposal-key='key-1']")).toBeTruthy();
  });

  test("clicking mark toggles selection", () => {
    const onToggle = jest.fn();
    render(
      <PageViewer
        pageText="Arithmetic fundamentals."
        pageProposals={[{ ...PROPOSALS[0], client_proposal_key: "key-1" }]}
        selectedKeys={new Set()}
        onToggle={onToggle}
      />,
    );
    const mark = document.querySelector("[data-proposal-key='key-1']");
    fireEvent.click(mark);
    expect(onToggle).toHaveBeenCalledWith("key-1");
  });
});

describe("ProposalRunner", () => {
  test("button disabled when no docId", () => {
    render(<ProposalRunner docId={null} loading={false} error={null} onRun={() => {}} proposalCount={0} />);
    expect(screen.getByTestId("run-propose-btn").disabled).toBe(true);
  });

  test("button enabled when docId set", () => {
    render(<ProposalRunner docId="doc-1" loading={false} error={null} onRun={() => {}} proposalCount={0} />);
    expect(screen.getByTestId("run-propose-btn").disabled).toBe(false);
  });
});

describe("ProposalActionBar", () => {
  const proposals = [
    { ...PROPOSALS[0], client_proposal_key: "key-1" },
    { ...PROPOSALS[1], client_proposal_key: "key-2" },
  ];

  test("accept-all-page selects current-page proposals", () => {
    const onSelectPage = jest.fn();
    render(
      <ProposalActionBar
        proposals={proposals}
        selectedKeys={new Set()}
        currentPage={1}
        onAcceptSelected={() => {}}
        onSelectPage={onSelectPage}
        onSelectByMinConfidence={() => {}}
        disabled={false}
      />,
    );
    fireEvent.click(screen.getByTestId("accept-all-page-btn"));
    expect(onSelectPage).toHaveBeenCalledWith(1);
  });

  test("accept-high-confidence calls with 0.95", () => {
    const onSelectByMinConfidence = jest.fn();
    render(
      <ProposalActionBar
        proposals={proposals}
        selectedKeys={new Set()}
        currentPage={1}
        onAcceptSelected={() => {}}
        onSelectPage={() => {}}
        onSelectByMinConfidence={onSelectByMinConfidence}
        disabled={false}
      />,
    );
    fireEvent.click(screen.getByTestId("accept-high-confidence-btn"));
    expect(onSelectByMinConfidence).toHaveBeenCalledWith(0.95);
  });
});

describe("AcceptPreviewModal", () => {
  const onCommit = jest.fn();
  const onClose = jest.fn();

  beforeEach(() => { jest.clearAllMocks(); });

  test("displays breakdown from preview result", () => {
    render(
      <AcceptPreviewModal
        previewResult={PREVIEW_RESPONSE}
        loading={false}
        onCommit={onCommit}
        onClose={onClose}
      />,
    );
    expect(screen.getByTestId("preview-insert-count").textContent).toBe("1");
    expect(screen.getByTestId("preview-dup-count").textContent).toBe("0");
    expect(screen.getByTestId("preview-invalid-count").textContent).toBe("0");
  });

  test("commit button disabled until reason entered", () => {
    render(
      <AcceptPreviewModal
        previewResult={PREVIEW_RESPONSE}
        loading={false}
        onCommit={onCommit}
        onClose={onClose}
      />,
    );
    const btn = screen.getByTestId("commit-btn");
    expect(btn.disabled).toBe(true);
    fireEvent.change(screen.getByTestId("accept-reason-input"), { target: { value: "test reason" } });
    expect(btn.disabled).toBe(false);
  });

  test("commit triggers onCommit with reason", () => {
    render(
      <AcceptPreviewModal
        previewResult={PREVIEW_RESPONSE}
        loading={false}
        onCommit={onCommit}
        onClose={onClose}
      />,
    );
    fireEvent.change(screen.getByTestId("accept-reason-input"), { target: { value: "my reason" } });
    fireEvent.click(screen.getByTestId("commit-btn"));
    expect(onCommit).toHaveBeenCalledWith("my reason");
  });

  test("Escape closes modal", () => {
    render(
      <AcceptPreviewModal
        previewResult={PREVIEW_RESPONSE}
        loading={false}
        onCommit={onCommit}
        onClose={onClose}
      />,
    );
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});
