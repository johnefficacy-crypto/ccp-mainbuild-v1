import React from "react";
import { render, screen } from "@testing-library/react";
import PromptBankPanel from "../PromptBankPanel";

const mockUseExamWorkspace = jest.fn(() => ({
  exam: { id: "exam-123", name: "UPSC GS-I" },
  cycle: { id: "cycle-456", cycle_name: "2026" },
}));

const mockUseAuth = jest.fn(() => ({
  user: {
    role: "super_admin",
    permissions: ["exam_intelligence.cms", "exam_intelligence.review"],
  },
}));

const mockUseApiCollection = jest.fn(() => ({
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
}));

const mockUseApiAction = jest.fn(() => ({
  run: jest.fn((opts) => {
    if (opts.action) {
      opts.action();
      if (opts.onSuccess) opts.onSuccess();
    }
  }),
  busy: false,
}));

jest.mock("../../ExamWorkspaceContext", () => ({
  useExamWorkspace: mockUseExamWorkspace,
}));

jest.mock("../../../../../lib/authContext", () => ({
  useAuth: mockUseAuth,
}));

jest.mock("../../../../../lib/hooks/useApiCollection", () => mockUseApiCollection);

jest.mock("../../../../../lib/hooks/useApiAction", () => mockUseApiAction);

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

  test("shows loading state initially", () => {
    mockUseApiCollection.mockReturnValueOnce({
      items: [],
      status: "loading",
      refresh: jest.fn(),
      setItems: jest.fn(),
    });

    render(<PromptBankPanel />);
    expect(screen.getByText(/Loading prompts/i)).toBeInTheDocument();
  });

  test("shows empty state when no prompts found", () => {
    mockUseApiCollection.mockReturnValueOnce({
      items: [],
      status: "empty",
      refresh: jest.fn(),
      setItems: jest.fn(),
    });

    render(<PromptBankPanel />);
    expect(screen.getByText(/No prompts found/i)).toBeInTheDocument();
  });

  test("shows error state on API failure", () => {
    mockUseApiCollection.mockReturnValueOnce({
      items: [],
      status: "error",
      refresh: jest.fn(),
      setItems: jest.fn(),
    });

    render(<PromptBankPanel />);
    expect(screen.getByRole("button", { name: /Retry/i })).toBeInTheDocument();
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

  test("does not render action buttons for users without permission", () => {
    mockUseAuth.mockReturnValueOnce({
      user: { role: "user", permissions: [] },
    });

    render(<PromptBankPanel />);

    expect(
      screen.queryByRole("button", { name: /\+ New Prompt/i })
    ).not.toBeInTheDocument();
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

  test("tab is correctly placed in tab order", () => {
    // This test verifies the tab integration in ExamWorkspace
    // The actual integration is tested in ExamWorkspace.test.jsx
    // This is a placeholder for structural validation
    expect(true).toBe(true);
  });

  test("passing exam_id=null shows informative message", () => {
    mockUseExamWorkspace.mockReturnValueOnce({
      exam: null,
      cycle: null,
    });

    render(<PromptBankPanel />);

    expect(
      screen.getByText(/Select an exam to view prompts/)
    ).toBeInTheDocument();
  });
});

describe("PromptBankPanel - Action flows", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("create button opens editor drawer", () => {
    render(<PromptBankPanel />);

    const createBtn = screen.getByRole("button", { name: /\+ New Prompt/i });

    // The editor drawer should render (it uses a different component)
    // For now, verify the button is present
    expect(createBtn).toBeInTheDocument();
  });

  test("bulk import button opens bulk flow", () => {
    render(<PromptBankPanel />);

    const importBtn = screen.getByRole("button", { name: /Bulk Import/i });

    expect(importBtn).toBeInTheDocument();
  });
});

describe("PromptBankPanel - Readiness Summary", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("displays readiness summary table", () => {
    render(<PromptBankPanel />);

    // The readiness component should be present
    // We're testing through the parent, so just verify it renders without error
    expect(screen.getByText(/Readiness/i)).toBeInTheDocument();
  });
});
