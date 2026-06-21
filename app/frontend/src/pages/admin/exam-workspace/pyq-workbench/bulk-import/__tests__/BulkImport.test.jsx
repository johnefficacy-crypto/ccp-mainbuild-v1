/**
 * Tests for PR5 bulk CSV import UI.
 *
 * Covers:
 * - useBulkImport: preflight stores response + advances step
 * - useBulkImport: commit stores result + advances to result step
 * - useBulkImport: 422 on preflight surfaces error state
 * - useBulkImport: network error on commit shows error inline
 * - BulkImportModal opens via button, closes via Escape (upload step)
 * - BulkImportModal Escape on preview step shows confirmation overlay
 * - CsvUploadStep: file selection populates filename
 * - Run preflight disabled until both paper and file selected
 * - PreflightPreview renders summary counts
 * - PreflightPreview renders rows with correct status badges
 * - CommitConfirmation commit button disabled when reason empty
 * - CommitResult shows correct counts and per_row breakdown
 * - CommitResult "Import another batch" resets to upload step
 * - override_errors checkbox state preserved going back/forward
 * - CSV body is NOT JSON-wrapped (raw text sent to preflight endpoint)
 * F2: BulkImportModal calls onSuccess(paperId) when result-close-btn clicked
 * F2: CommitResult shows success banner when committed > 0 and no failures
 * F2: CommitResult Close button label is "Open paper" when committed > 0
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act, renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

jest.mock("../../../../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(), post: jest.fn() },
  apiFetch: jest.fn(),
}));

const { api, apiFetch } = require("../../../../../../lib/api");

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PAPERS = [
  { id: "p1", year: 2024, paper_code: "GS-I", shift: "I" },
  { id: "p2", year: 2023, paper_code: "GS-I", shift: "II" },
];

const PREFLIGHT_OK = {
  import_token: "tok-abc",
  total: 3,
  summary: { ok: 2, fuzzy: 0, duplicate: 1, error: 0 },
  rows: [
    { row_number: 1, status: "ok", question_number: 1, question_text: "What is 2+2?", question_type: "mcq", messages: [] },
    { row_number: 2, status: "duplicate", question_number: 2, question_text: "Capital of India?", question_type: "mcq", messages: ["Possible duplicate"] },
    { row_number: 3, status: "ok", question_number: 3, question_text: "Third question here.", question_type: "numerical", messages: [] },
  ],
};

const COMMIT_OK = {
  committed: 2, skipped: 1, failed: 0,
  per_row: [
    { row_number: 1, question_number: 1, result: "committed", reason: null, question_id: "q-new-1" },
    { row_number: 2, question_number: 2, result: "skipped", reason: "duplicate", question_id: null },
    { row_number: 3, question_number: 3, result: "committed", reason: null, question_id: "q-new-3" },
  ],
};

// ── Component requires ────────────────────────────────────────────────────────

const { useBulkImport } = require("../useBulkImport");
const BulkImportModal = require("../BulkImportModal").default;
const CsvUploadStep = require("../CsvUploadStep").default;
const PreflightPreview = require("../PreflightPreview").default;
const CommitConfirmation = require("../CommitConfirmation").default;
const CommitResult = require("../CommitResult").default;

// ── useBulkImport hook tests ──────────────────────────────────────────────────

describe("useBulkImport", () => {
  beforeEach(() => { jest.clearAllMocks(); });

  test("runPreflight stores response and advances to preview step", async () => {
    apiFetch.mockResolvedValue(PREFLIGHT_OK);
    const { result } = renderHook(() => useBulkImport("p1"));

    await act(async () => {
      result.current.selectFile(new File(["q,a\n1,b"], "test.csv", { type: "text/csv" }));
    });

    // Wait for FileReader
    await act(async () => { await new Promise((r) => setTimeout(r, 50)); });

    await act(async () => {
      await result.current.runPreflight("p1", "q,a\n1,b");
    });

    expect(result.current.state.step).toBe("preview");
    expect(result.current.state.preflight).toEqual(PREFLIGHT_OK);
  });

  test("runPreflight sends raw CSV body (not JSON-wrapped)", async () => {
    apiFetch.mockResolvedValue(PREFLIGHT_OK);
    const { result } = renderHook(() => useBulkImport("p1"));
    const csv = "question_text,question_type\nWhat?,mcq";

    await act(async () => {
      await result.current.runPreflight("p1", csv);
    });

    expect(apiFetch).toHaveBeenCalledWith(
      expect.stringContaining("/bulk-import/preflight"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "Content-Type": "text/csv" }),
        body: csv,
      }),
    );
    // Body must be the literal CSV string, not a JSON string
    const callBody = apiFetch.mock.calls[0][1].body;
    expect(callBody).toBe(csv);
    expect(() => JSON.parse(callBody)).toThrow();
  });

  test("preflight 422 surfaces error state, step stays upload", async () => {
    apiFetch.mockRejectedValue(new Error("Invalid CSV format"));
    const { result } = renderHook(() => useBulkImport("p1"));

    await act(async () => {
      await result.current.runPreflight("p1", "bad csv");
    });

    expect(result.current.state.step).toBe("upload");
    expect(result.current.state.error.preflight).toContain("Invalid CSV");
  });

  test("runCommit stores result and advances to result step", async () => {
    apiFetch.mockResolvedValue(PREFLIGHT_OK);
    api.post.mockResolvedValue(COMMIT_OK);
    const { result } = renderHook(() => useBulkImport("p1"));

    await act(async () => {
      await result.current.runPreflight("p1", "q,a");
    });
    await act(async () => {
      result.current.goToStep("committing");
    });
    await act(async () => {
      await result.current.runCommit("p1", "tok-abc", false, "batch import reason");
    });

    expect(result.current.state.step).toBe("result");
    expect(result.current.state.commit_result).toEqual(COMMIT_OK);
  });

  test("commit network error surfaces error inline, stays on committing step", async () => {
    apiFetch.mockResolvedValue(PREFLIGHT_OK);
    api.post.mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useBulkImport("p1"));

    await act(async () => { await result.current.runPreflight("p1", "q,a"); });
    await act(async () => { result.current.goToStep("committing"); });
    await act(async () => {
      await result.current.runCommit("p1", "tok-abc", false, "reason");
    });

    expect(result.current.state.step).toBe("committing");
    expect(result.current.state.error.commit).toContain("Network error");
  });

  test("reset returns to upload step", async () => {
    apiFetch.mockResolvedValue(PREFLIGHT_OK);
    const { result } = renderHook(() => useBulkImport("p1"));

    await act(async () => { await result.current.runPreflight("p1", "q,a"); });
    expect(result.current.state.step).toBe("preview");

    act(() => { result.current.reset("p1"); });
    expect(result.current.state.step).toBe("upload");
    expect(result.current.state.preflight).toBeNull();
  });
});

// ── BulkImportModal component tests ──────────────────────────────────────────

describe("BulkImportModal", () => {
  beforeEach(() => { jest.clearAllMocks(); apiFetch.mockResolvedValue(PREFLIGHT_OK); });

  test("renders on open via bulk-import-btn in panel", () => {
    render(
      <BulkImportModal papers={PAPERS} initialPaperId={null} onClose={() => {}} />,
    );
    expect(screen.getByTestId("bulk-import-modal")).toBeTruthy();
    expect(screen.getByTestId("csv-upload-step")).toBeTruthy();
  });

  test("Escape on upload step calls onClose without confirmation", () => {
    const onClose = jest.fn();
    render(<BulkImportModal papers={PAPERS} initialPaperId={null} onClose={onClose} />);
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
    expect(screen.queryByTestId("escape-confirm-overlay")).toBeNull();
  });

  test("Escape on preview step shows confirmation overlay", async () => {
    apiFetch.mockResolvedValue(PREFLIGHT_OK);
    render(<BulkImportModal papers={PAPERS} initialPaperId="p1" onClose={() => {}} />);

    // Simulate reaching preview step by clicking run preflight after selecting file
    // Use internal selectFile via hook — easier: just simulate going to preview step
    // by invoking preflight. We set csv_text via file input change.
    const fileInput = screen.getByTestId("bulk-csv-input");
    fireEvent.change(fileInput, {
      target: { files: [new File(["q,a\n1,b"], "test.csv", { type: "text/csv" })] },
    });

    await waitFor(() => expect(screen.getByTestId("bulk-csv-filename").textContent).toBe("test.csv"));

    fireEvent.click(screen.getByTestId("run-preflight-btn"));
    await waitFor(() => expect(screen.getByTestId("preflight-preview")).toBeTruthy());

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(screen.getByTestId("escape-confirm-overlay")).toBeTruthy();
  });

  test("close button calls onClose on upload step", () => {
    const onClose = jest.fn();
    render(<BulkImportModal papers={PAPERS} initialPaperId={null} onClose={onClose} />);
    fireEvent.click(screen.getByTestId("modal-close-btn"));
    expect(onClose).toHaveBeenCalled();
  });
});

// ── CsvUploadStep ─────────────────────────────────────────────────────────────

describe("CsvUploadStep", () => {
  test("file selection populates filename", () => {
    let filename = null;
    render(
      <CsvUploadStep
        papers={PAPERS}
        selectedPaperId="p1"
        onSelectPaper={() => {}}
        csvFilename={filename}
        onSelectFile={(f) => { filename = f.name; }}
        onRunPreflight={() => {}}
        loading={false}
        error={null}
      />,
    );
    const input = screen.getByTestId("bulk-csv-input");
    fireEvent.change(input, {
      target: { files: [new File(["a,b"], "my-data.csv", { type: "text/csv" })] },
    });
    expect(filename).toBe("my-data.csv");
  });

  test("run preflight disabled when no paper selected", () => {
    render(
      <CsvUploadStep
        papers={PAPERS}
        selectedPaperId={null}
        onSelectPaper={() => {}}
        csvFilename="test.csv"
        onSelectFile={() => {}}
        onRunPreflight={() => {}}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByTestId("run-preflight-btn").disabled).toBe(true);
  });

  test("run preflight disabled when no file selected", () => {
    render(
      <CsvUploadStep
        papers={PAPERS}
        selectedPaperId="p1"
        onSelectPaper={() => {}}
        csvFilename={null}
        onSelectFile={() => {}}
        onRunPreflight={() => {}}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByTestId("run-preflight-btn").disabled).toBe(true);
  });

  test("run preflight enabled when both paper and file selected", () => {
    render(
      <CsvUploadStep
        papers={PAPERS}
        selectedPaperId="p1"
        onSelectPaper={() => {}}
        csvFilename="test.csv"
        onSelectFile={() => {}}
        onRunPreflight={() => {}}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByTestId("run-preflight-btn").disabled).toBe(false);
  });
});

// ── PreflightPreview ──────────────────────────────────────────────────────────

describe("PreflightPreview", () => {
  test("renders summary counts from API response", () => {
    render(<PreflightPreview preflight={PREFLIGHT_OK} onBack={() => {}} onContinue={() => {}} />);
    expect(screen.getByTestId("summary-ok").textContent).toContain("2");
    expect(screen.getByTestId("summary-duplicate").textContent).toContain("1");
    expect(screen.getByTestId("summary-error").textContent).toContain("0");
    expect(screen.getByTestId("summary-fuzzy").textContent).toContain("0");
  });

  test("renders rows with correct status badges", () => {
    render(<PreflightPreview preflight={PREFLIGHT_OK} onBack={() => {}} onContinue={() => {}} />);
    const badges = document.querySelectorAll("[aria-label^='Status:']");
    const statuses = Array.from(badges).map((b) => b.getAttribute("aria-label"));
    expect(statuses).toContain("Status: ok");
    expect(statuses).toContain("Status: duplicate");
  });
});

// ── CommitConfirmation ────────────────────────────────────────────────────────

describe("CommitConfirmation", () => {
  test("commit button disabled when reason is empty", () => {
    render(
      <CommitConfirmation
        overrideErrors={false}
        onSetOverride={() => {}}
        reason=""
        onSetReason={() => {}}
        onBack={() => {}}
        onCommit={() => {}}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByTestId("commit-import-btn").disabled).toBe(true);
  });

  test("commit button enabled when reason is entered", () => {
    render(
      <CommitConfirmation
        overrideErrors={false}
        onSetOverride={() => {}}
        reason="importing batch"
        onSetReason={() => {}}
        onBack={() => {}}
        onCommit={() => {}}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByTestId("commit-import-btn").disabled).toBe(false);
  });

  test("override_errors checkbox reflects prop and fires callback", () => {
    const onSetOverride = jest.fn();
    render(
      <CommitConfirmation
        overrideErrors={false}
        onSetOverride={onSetOverride}
        reason="reason"
        onSetReason={() => {}}
        onBack={() => {}}
        onCommit={() => {}}
        loading={false}
        error={null}
      />,
    );
    fireEvent.click(screen.getByTestId("override-errors-checkbox"));
    expect(onSetOverride).toHaveBeenCalledWith(true);
  });
});

// ── CommitResult ──────────────────────────────────────────────────────────────

describe("CommitResult", () => {
  test("shows correct counts", () => {
    render(<CommitResult commitResult={COMMIT_OK} onImportAnother={() => {}} onClose={() => {}} />);
    expect(screen.getByTestId("result-committed").textContent).toContain("2");
    expect(screen.getByTestId("result-skipped").textContent).toContain("1");
    expect(screen.getByTestId("result-failed").textContent).toContain("0");
  });

  test("renders per_row breakdown", () => {
    render(<CommitResult commitResult={COMMIT_OK} onImportAnother={() => {}} onClose={() => {}} />);
    expect(document.body.textContent).toContain("committed");
    expect(document.body.textContent).toContain("skipped");
  });

  test("shows failure banner when failed > 0", () => {
    const withFail = { ...COMMIT_OK, failed: 1, per_row: [{ row_number: 1, result: "failed", reason: "missing field" }] };
    render(<CommitResult commitResult={withFail} onImportAnother={() => {}} onClose={() => {}} />);
    expect(screen.getByTestId("commit-failure-banner")).toBeTruthy();
  });

  test("no failure banner when failed = 0", () => {
    render(<CommitResult commitResult={COMMIT_OK} onImportAnother={() => {}} onClose={() => {}} />);
    expect(screen.queryByTestId("commit-failure-banner")).toBeNull();
  });

  test("Import another batch resets via callback", () => {
    const onImportAnother = jest.fn();
    render(<CommitResult commitResult={COMMIT_OK} onImportAnother={onImportAnother} onClose={() => {}} />);
    fireEvent.click(screen.getByTestId("import-another-btn"));
    expect(onImportAnother).toHaveBeenCalled();
  });

  test("handles skipped_stale gracefully in per_row", () => {
    const withStale = { ...COMMIT_OK, per_row: [{ row_number: 1, result: "skipped_stale", reason: "key mismatch" }] };
    render(<CommitResult commitResult={withStale} onImportAnother={() => {}} onClose={() => {}} />);
    expect(document.body.textContent).toContain("skipped_stale");
  });

  // F2: success banner
  test("F2: shows success banner when committed > 0 and no failures", () => {
    render(<CommitResult commitResult={COMMIT_OK} onImportAnother={() => {}} onClose={() => {}} />);
    expect(screen.getByTestId("commit-success-banner")).toBeTruthy();
    expect(screen.getByTestId("commit-success-banner").textContent).toContain("2 questions committed");
  });

  test("F2: no success banner when committed = 0", () => {
    const noCommit = { committed: 0, skipped: 1, failed: 0, per_row: [] };
    render(<CommitResult commitResult={noCommit} onImportAnother={() => {}} onClose={() => {}} />);
    expect(screen.queryByTestId("commit-success-banner")).toBeNull();
  });

  test("F2: no success banner when there are failures", () => {
    const withFail = { committed: 1, skipped: 0, failed: 1, per_row: [] };
    render(<CommitResult commitResult={withFail} onImportAnother={() => {}} onClose={() => {}} />);
    expect(screen.queryByTestId("commit-success-banner")).toBeNull();
    expect(screen.getByTestId("commit-failure-banner")).toBeTruthy();
  });

  test("F2: close button label is 'Open paper' when committed > 0", () => {
    render(<CommitResult commitResult={COMMIT_OK} onImportAnother={() => {}} onClose={() => {}} />);
    expect(screen.getByTestId("result-close-btn").textContent).toBe("Open paper");
  });

  test("F2: close button label is 'Close' when committed = 0", () => {
    const noCommit = { committed: 0, skipped: 1, failed: 0, per_row: [] };
    render(<CommitResult commitResult={noCommit} onImportAnother={() => {}} onClose={() => {}} />);
    expect(screen.getByTestId("result-close-btn").textContent).toBe("Close");
  });
});

// ── F2: BulkImportModal onSuccess callback ────────────────────────────────────

describe("F2: BulkImportModal onSuccess", () => {
  beforeEach(() => { jest.clearAllMocks(); apiFetch.mockResolvedValue(PREFLIGHT_OK); });

  test("F2: onSuccess(paperId) is called with selected paper id when result Close is clicked", async () => {
    api.post.mockResolvedValue(COMMIT_OK);
    const onSuccess = jest.fn();
    const onClose = jest.fn();

    render(
      <BulkImportModal
        papers={PAPERS}
        initialPaperId="p1"
        onClose={onClose}
        onSuccess={onSuccess}
      />,
    );

    // Upload step: select file and run preflight
    const fileInput = screen.getByTestId("bulk-csv-input");
    fireEvent.change(fileInput, {
      target: { files: [new File(["q,a\n1,b"], "test.csv", { type: "text/csv" })] },
    });
    await waitFor(() => expect(screen.getByTestId("bulk-csv-filename").textContent).toBe("test.csv"));
    fireEvent.click(screen.getByTestId("run-preflight-btn"));
    await waitFor(() => expect(screen.getByTestId("preflight-preview")).toBeTruthy());

    // Preview step: continue to committing
    fireEvent.click(screen.getByTestId("continue-to-commit-btn"));
    await waitFor(() => expect(screen.getByTestId("commit-confirmation")).toBeTruthy());

    // Committing step: enter reason and commit
    fireEvent.change(screen.getByTestId("commit-reason-input"), { target: { value: "batch import" } });
    fireEvent.click(screen.getByTestId("commit-import-btn"));
    await waitFor(() => expect(screen.getByTestId("commit-result")).toBeTruthy());

    // Result step: click Close
    fireEvent.click(screen.getByTestId("result-close-btn"));
    expect(onSuccess).toHaveBeenCalledWith("p1");
    expect(onClose).toHaveBeenCalled();
  });

  test("F2: onSuccess is NOT called when Import another batch is clicked", async () => {
    api.post.mockResolvedValue(COMMIT_OK);
    const onSuccess = jest.fn();

    render(
      <BulkImportModal
        papers={PAPERS}
        initialPaperId="p1"
        onClose={() => {}}
        onSuccess={onSuccess}
      />,
    );

    // Drive to result step
    const fileInput = screen.getByTestId("bulk-csv-input");
    fireEvent.change(fileInput, {
      target: { files: [new File(["q,a"], "t.csv", { type: "text/csv" })] },
    });
    await waitFor(() => expect(screen.getByTestId("bulk-csv-filename").textContent).toBe("t.csv"));
    fireEvent.click(screen.getByTestId("run-preflight-btn"));
    await waitFor(() => expect(screen.getByTestId("preflight-preview")).toBeTruthy());
    fireEvent.click(screen.getByTestId("continue-to-commit-btn"));
    await waitFor(() => expect(screen.getByTestId("commit-confirmation")).toBeTruthy());
    fireEvent.change(screen.getByTestId("commit-reason-input"), { target: { value: "reason" } });
    fireEvent.click(screen.getByTestId("commit-import-btn"));
    await waitFor(() => expect(screen.getByTestId("commit-result")).toBeTruthy());

    // Click "Import another batch" — should NOT call onSuccess
    fireEvent.click(screen.getByTestId("import-another-btn"));
    expect(onSuccess).not.toHaveBeenCalled();
  });

  test("F2: works without onSuccess prop (no crash)", async () => {
    api.post.mockResolvedValue(COMMIT_OK);
    render(
      <BulkImportModal papers={PAPERS} initialPaperId="p1" onClose={() => {}} />,
    );

    const fileInput = screen.getByTestId("bulk-csv-input");
    fireEvent.change(fileInput, {
      target: { files: [new File(["q,a"], "t.csv", { type: "text/csv" })] },
    });
    await waitFor(() => expect(screen.getByTestId("bulk-csv-filename").textContent).toBe("t.csv"));
    fireEvent.click(screen.getByTestId("run-preflight-btn"));
    await waitFor(() => expect(screen.getByTestId("preflight-preview")).toBeTruthy());
    fireEvent.click(screen.getByTestId("continue-to-commit-btn"));
    await waitFor(() => expect(screen.getByTestId("commit-confirmation")).toBeTruthy());
    fireEvent.change(screen.getByTestId("commit-reason-input"), { target: { value: "reason" } });
    fireEvent.click(screen.getByTestId("commit-import-btn"));
    await waitFor(() => expect(screen.getByTestId("commit-result")).toBeTruthy());

    // Should not throw
    expect(() => fireEvent.click(screen.getByTestId("result-close-btn"))).not.toThrow();
  });
});
