import React from "react";
import { render, screen } from "@testing-library/react";
import PromptBankPanel from "../PromptBankPanel";

jest.mock("../../ExamWorkspaceContext", () => ({
  useExamWorkspace: jest.fn(() => ({
    exam: { id: "exam-123", name: "UPSC GS-I" },
    cycle: { id: "cycle-456", cycle_name: "2026" },
  })),
}));

jest.mock("../../../../../lib/authContext", () => ({
  useAuth: jest.fn(() => ({
    user: {
      role: "super_admin",
      permissions: ["exam_intelligence.cms", "exam_intelligence.review"],
    },
  })),
}));

jest.mock("../../../../../lib/hooks/useApiCollection", () =>
  jest.fn(() => ({
    items: [
      {
        id: "prompt-1",
        prompt_text: "Construct a simple sentence.",
        exercise_type: "sentence_construction",
        topic_name: "Sentence Construction",
        difficulty_level: 3,
        min_words: 5,
        max_words: 20,
        reviewer_status: "verified",
        is_active: true,
        updated_at: "2026-07-02T10:00:00Z",
      },
    ],
    status: "live",
    refresh: jest.fn(),
    setItems: jest.fn(),
  }))
);

jest.mock("../../../../../lib/hooks/useApiAction", () =>
  jest.fn(() => ({
    run: jest.fn((opts) => {
      if (opts.action) {
        opts.action();
        if (opts.onSuccess) opts.onSuccess();
      }
    }),
    busy: false,
  }))
);

jest.mock("../promptBankApi", () => ({
  promptBankApi: {
    listPrompts: jest.fn(),
    createPrompt: jest.fn(),
    reviewPrompt: jest.fn(),
    setActivation: jest.fn(),
    bulkImportPrompts: jest.fn(),
    clonePrompt: jest.fn(),
  },
}));

describe("PromptBankPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders the panel with heading", () => {
    render(<PromptBankPanel />);
    expect(screen.getByText(/Readiness/i)).toBeInTheDocument();
  });

  test("shows table with prompts when data loads", () => {
    render(<PromptBankPanel />);

    expect(screen.getByText(/Construct a simple sentence/)).toBeInTheDocument();
    expect(screen.getByText(/Sentence construction/)).toBeInTheDocument();
  });

  test("renders create and bulk import buttons for operators with cms permission", () => {
    render(<PromptBankPanel />);

    expect(
      screen.getByRole("button", { name: /\+ New Prompt/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Bulk Import/i })
    ).toBeInTheDocument();
  });

  test("renders filter bar with select dropdowns", () => {
    render(<PromptBankPanel />);

    expect(screen.getByLabelText(/Search/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Exercise Type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Reviewer Status/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Active Status/i)).toBeInTheDocument();
  });

  test("prompt table shows expected columns", () => {
    render(<PromptBankPanel />);

    expect(screen.getByText(/Prompt/)).toBeInTheDocument();
    expect(screen.getByText(/Exercise type/)).toBeInTheDocument();
    expect(screen.getByText(/Topic/)).toBeInTheDocument();
    expect(screen.getByText(/Difficulty/)).toBeInTheDocument();
    expect(screen.getByText(/Word limit/)).toBeInTheDocument();
    expect(screen.getByText(/Reviewer status/)).toBeInTheDocument();
    expect(screen.getByText(/Active/)).toBeInTheDocument();
  });

  test("displays readiness summary table", () => {
    render(<PromptBankPanel />);
    expect(screen.getByText(/Readiness/i)).toBeInTheDocument();
  });
});
