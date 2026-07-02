import { render, screen, fireEvent } from "@testing-library/react";
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

    test("clears the autosaved draft after a successful submit", () => {
      const onSubmit = jest.fn();
      render(<SentenceBuilder unitNumber={2} sessionId="S1" onSubmit={onSubmit} />);
      fireEvent.change(screen.getByTestId("sentence-input"), { target: { value: "final answer" } });
      fireEvent.click(screen.getByTestId("sentence-submit"));
      expect(onSubmit).toHaveBeenCalledWith("final answer");
      expect(window.sessionStorage.getItem("ewp:draft:S1:2")).toBeNull();
    });
  });
});
