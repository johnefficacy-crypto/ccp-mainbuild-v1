import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ParagraphBuilder, {
  isParagraphExercise,
  PARAGRAPH_EXERCISE_TYPES,
} from "./ParagraphBuilder";

describe("isParagraphExercise", () => {
  test("matches the backend paragraph exercise set, and nothing else", () => {
    for (const t of PARAGRAPH_EXERCISE_TYPES) expect(isParagraphExercise(t)).toBe(true);
    expect(isParagraphExercise("paragraph_writing")).toBe(true);
    expect(isParagraphExercise("essay_practice")).toBe(true);
    expect(isParagraphExercise("sentence_construction")).toBe(false);
    expect(isParagraphExercise("sentence_correction")).toBe(false);
    expect(isParagraphExercise(undefined)).toBe(false);
    expect(isParagraphExercise("")).toBe(false);
  });
});

describe("ParagraphBuilder", () => {
  test("typing updates the word count with the backend-parity tokeniser", () => {
    render(<ParagraphBuilder unitNumber={1} onSubmit={() => {}} />);
    fireEvent.change(screen.getByTestId("paragraph-input"), {
      target: { value: "one two three four" },
    });
    expect(screen.getByText(/4 words/)).toBeInTheDocument();
  });

  test("clicking submit calls onSubmit with the trimmed body", () => {
    const onSubmit = jest.fn();
    render(<ParagraphBuilder unitNumber={2} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByTestId("paragraph-input"), {
      target: { value: "  a short paragraph body  " },
    });
    fireEvent.click(screen.getByTestId("paragraph-submit"));
    expect(onSubmit).toHaveBeenCalledWith("a short paragraph body");
  });

  test("submit disabled when empty", () => {
    render(<ParagraphBuilder unitNumber={1} onSubmit={() => {}} />);
    expect(screen.getByTestId("paragraph-submit")).toBeDisabled();
  });

  test("submit disabled when busy", () => {
    render(<ParagraphBuilder unitNumber={1} initialValue="text" busy onSubmit={() => {}} />);
    expect(screen.getByTestId("paragraph-submit")).toBeDisabled();
  });

  test("renders promptText and read-only source context", () => {
    render(
      <ParagraphBuilder
        unitNumber={1}
        promptText="Write about your city"
        sourceText="The passage to summarise."
        exerciseType="summary_writing"
        onSubmit={() => {}}
      />,
    );
    expect(screen.getByText("Write about your city")).toBeInTheDocument();
    expect(screen.getByTestId("source-context")).toBeInTheDocument();
    expect(screen.getByTestId("source-context-label")).toHaveTextContent("Source passage");
  });

  describe("outline scratchpad", () => {
    test("starts with one point and can add and edit points", () => {
      render(<ParagraphBuilder unitNumber={1} onSubmit={() => {}} />);
      expect(screen.getByTestId("paragraph-outline")).toBeInTheDocument();
      expect(screen.getByTestId("paragraph-outline-point-0")).toBeInTheDocument();
      expect(screen.queryByTestId("paragraph-outline-point-1")).not.toBeInTheDocument();

      fireEvent.click(screen.getByTestId("paragraph-outline-add"));
      const second = screen.getByTestId("paragraph-outline-point-1");
      fireEvent.change(second, { target: { value: "supporting idea" } });
      expect(second).toHaveValue("supporting idea");
    });

    test("the last point cannot be removed; extra points can", () => {
      render(<ParagraphBuilder unitNumber={1} onSubmit={() => {}} />);
      // Only one point → remove is disabled.
      expect(screen.getByTestId("paragraph-outline-remove-0")).toBeDisabled();
      fireEvent.click(screen.getByTestId("paragraph-outline-add"));
      expect(screen.getByTestId("paragraph-outline-remove-1")).not.toBeDisabled();
      fireEvent.click(screen.getByTestId("paragraph-outline-remove-1"));
      expect(screen.queryByTestId("paragraph-outline-point-1")).not.toBeInTheDocument();
    });
  });

  describe("autosave", () => {
    beforeEach(() => window.sessionStorage.clear());

    test("persists the draft to sessionStorage keyed by session + unit", () => {
      render(<ParagraphBuilder unitNumber={2} sessionId="S1" onSubmit={() => {}} />);
      fireEvent.change(screen.getByTestId("paragraph-input"), {
        target: { value: "work in progress" },
      });
      expect(window.sessionStorage.getItem("ewp:draft:S1:2")).toBe("work in progress");
    });

    test("restores an autosaved draft on mount", () => {
      window.sessionStorage.setItem("ewp:draft:S1:2", "restored body");
      render(<ParagraphBuilder unitNumber={2} sessionId="S1" onSubmit={() => {}} />);
      expect(screen.getByTestId("paragraph-input")).toHaveValue("restored body");
    });

    test("persists and restores the outline plan (outline_json)", () => {
      const { unmount } = render(
        <ParagraphBuilder unitNumber={3} sessionId="S1" onSubmit={() => {}} />,
      );
      fireEvent.change(screen.getByTestId("paragraph-outline-point-0"), {
        target: { value: "topic sentence" },
      });
      const stored = JSON.parse(window.sessionStorage.getItem("ewp:outline:S1:3"));
      expect(Array.isArray(stored)).toBe(true);
      expect(stored[0].text).toBe("topic sentence");

      unmount();
      render(<ParagraphBuilder unitNumber={3} sessionId="S1" onSubmit={() => {}} />);
      expect(screen.getByTestId("paragraph-outline-point-0")).toHaveValue("topic sentence");
    });

    test("clears BOTH draft and outline only after a SUCCESSFUL submit", async () => {
      const onSubmit = jest.fn().mockResolvedValue({ ok: true });
      render(<ParagraphBuilder unitNumber={2} sessionId="S1" onSubmit={onSubmit} />);
      fireEvent.change(screen.getByTestId("paragraph-outline-point-0"), {
        target: { value: "plan" },
      });
      fireEvent.change(screen.getByTestId("paragraph-input"), {
        target: { value: "final paragraph" },
      });
      fireEvent.click(screen.getByTestId("paragraph-submit"));
      expect(onSubmit).toHaveBeenCalledWith("final paragraph");
      await waitFor(() => expect(window.sessionStorage.getItem("ewp:draft:S1:2")).toBeNull());
      expect(window.sessionStorage.getItem("ewp:outline:S1:2")).toBeNull();
    });

    test("preserves draft and outline when the submit fails", async () => {
      const onSubmit = jest.fn().mockResolvedValue({ ok: false });
      render(<ParagraphBuilder unitNumber={2} sessionId="S1" onSubmit={onSubmit} />);
      fireEvent.change(screen.getByTestId("paragraph-outline-point-0"), {
        target: { value: "keep plan" },
      });
      fireEvent.change(screen.getByTestId("paragraph-input"), {
        target: { value: "keep me" },
      });
      fireEvent.click(screen.getByTestId("paragraph-submit"));
      await waitFor(() => expect(onSubmit).toHaveBeenCalled());
      expect(window.sessionStorage.getItem("ewp:draft:S1:2")).toBe("keep me");
      expect(JSON.parse(window.sessionStorage.getItem("ewp:outline:S1:2"))[0].text).toBe("keep plan");
    });
  });
});
