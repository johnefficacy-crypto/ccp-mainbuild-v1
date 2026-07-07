import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SentenceBuilder from "./SentenceBuilder";

describe("SentenceBuilder", () => {
  test("typing updates the word count", () => {
    render(<SentenceBuilder unitNumber={1} onSubmit={() => {}} />);
    const input = screen.getByTestId("sentence-input");
    fireEvent.change(input, { target: { value: "one two three" } });
    expect(screen.getByText(/3 words/)).toBeInTheDocument();
  });

  test("clicking submit calls onSubmit with the typed text", () => {
    const onSubmit = jest.fn();
    render(<SentenceBuilder unitNumber={2} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByTestId("sentence-input"), {
      target: { value: "  hello world  " },
    });
    fireEvent.click(screen.getByTestId("sentence-submit"));
    expect(onSubmit).toHaveBeenCalledWith("hello world");
  });

  test("submit disabled when empty", () => {
    render(<SentenceBuilder unitNumber={1} onSubmit={() => {}} />);
    expect(screen.getByTestId("sentence-submit")).toBeDisabled();
  });

  test("submit disabled when busy", () => {
    render(
      <SentenceBuilder
        unitNumber={1}
        initialValue="text"
        busy
        onSubmit={() => {}}
      />
    );
    expect(screen.getByTestId("sentence-submit")).toBeDisabled();
  });

  test("renders promptText", () => {
    render(
      <SentenceBuilder
        unitNumber={1}
        promptText="Describe your day"
        onSubmit={() => {}}
      />
    );
    expect(screen.getByText("Describe your day")).toBeInTheDocument();
  });

  test("renders read-only source context above the editor when sourceText is present", () => {
    render(
      <SentenceBuilder
        unitNumber={1}
        sourceText="He go to school."
        exerciseType="sentence_correction"
        onSubmit={() => {}}
      />
    );
    expect(screen.getByTestId("source-context")).toBeInTheDocument();
    expect(screen.getByTestId("source-context-label")).toHaveTextContent("Sentence to correct");
    // The source is not the answer field.
    expect(screen.getByTestId("source-context-text")).toHaveTextContent("He go to school.");
  });

  test("does not render source context when sourceText is absent", () => {
    render(<SentenceBuilder unitNumber={1} onSubmit={() => {}} />);
    expect(screen.queryByTestId("source-context")).not.toBeInTheDocument();
  });

  test("renders required-word chips when requiredWords are given", () => {
    render(
      <SentenceBuilder unitNumber={1} requiredWords={["diligent"]} onSubmit={() => {}} />
    );
    expect(screen.getByTestId("word-chips")).toBeInTheDocument();
    expect(screen.getByTestId("words-used")).toHaveTextContent("0/1");
  });

  describe("autosave", () => {
    beforeEach(() => window.sessionStorage.clear());

    test("persists the draft to sessionStorage keyed by session + unit", () => {
      render(<SentenceBuilder unitNumber={2} sessionId="S1" onSubmit={() => {}} />);
      fireEvent.change(screen.getByTestId("sentence-input"), { target: { value: "work in progress" } });
      expect(window.sessionStorage.getItem("ewp:draft:S1:2")).toBe("work in progress");
    });

    test("restores an autosaved draft on mount", () => {
      window.sessionStorage.setItem("ewp:draft:S1:2", "restored text");
      render(<SentenceBuilder unitNumber={2} sessionId="S1" onSubmit={() => {}} />);
      expect(screen.getByTestId("sentence-input")).toHaveValue("restored text");
    });

    test("clears the autosaved draft only after a SUCCESSFUL submit", async () => {
      const onSubmit = jest.fn().mockResolvedValue({ ok: true });
      render(<SentenceBuilder unitNumber={2} sessionId="S1" onSubmit={onSubmit} />);
      fireEvent.change(screen.getByTestId("sentence-input"), { target: { value: "final answer" } });
      fireEvent.click(screen.getByTestId("sentence-submit"));
      expect(onSubmit).toHaveBeenCalledWith("final answer");
      await waitFor(() => expect(window.sessionStorage.getItem("ewp:draft:S1:2")).toBeNull());
    });

    test("preserves the autosaved draft when the submit fails", async () => {
      const onSubmit = jest.fn().mockResolvedValue({ ok: false });
      render(<SentenceBuilder unitNumber={2} sessionId="S1" onSubmit={onSubmit} />);
      fireEvent.change(screen.getByTestId("sentence-input"), { target: { value: "keep me" } });
      fireEvent.click(screen.getByTestId("sentence-submit"));
      await waitFor(() => expect(onSubmit).toHaveBeenCalled());
      // Failed submit must not wipe the recoverable draft.
      expect(window.sessionStorage.getItem("ewp:draft:S1:2")).toBe("keep me");
    });
  });
});
