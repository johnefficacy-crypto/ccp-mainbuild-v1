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
});
