import { render, screen } from "@testing-library/react";
import SourceContext, { sourceContextLabel } from "./SourceContext";

describe("SourceContext", () => {
  test("renders the source text when present", () => {
    render(<SourceContext sourceText="He go to school." exerciseType="sentence_correction" />);
    expect(screen.getByTestId("source-context")).toBeInTheDocument();
    expect(screen.getByTestId("source-context-text")).toHaveTextContent("He go to school.");
  });

  test("renders nothing when source is null / empty / whitespace", () => {
    const { rerender } = render(<SourceContext sourceText={null} />);
    expect(screen.queryByTestId("source-context")).not.toBeInTheDocument();
    rerender(<SourceContext sourceText="" />);
    expect(screen.queryByTestId("source-context")).not.toBeInTheDocument();
    rerender(<SourceContext sourceText="   " />);
    expect(screen.queryByTestId("source-context")).not.toBeInTheDocument();
  });

  test("labels correction-type exercises 'Sentence to correct'", () => {
    render(<SourceContext sourceText="x" exerciseType="sentence_correction" />);
    expect(screen.getByTestId("source-context-label")).toHaveTextContent("Sentence to correct");
  });

  test("labels source/passage-bearing exercises 'Source passage'", () => {
    render(<SourceContext sourceText="x" exerciseType="summary_writing" />);
    expect(screen.getByTestId("source-context-label")).toHaveTextContent("Source passage");
  });

  test("uses a sensible default label for unknown source-bearing types", () => {
    expect(sourceContextLabel("something_else")).toBe("Task context");
    expect(sourceContextLabel("vocabulary_in_context")).toBe("Source passage");
  });

  test("is read-only and accessibly labelled (region, not an input)", () => {
    render(<SourceContext sourceText="He go home." exerciseType="sentence_correction" />);
    const region = screen.getByTestId("source-context");
    // Announced via label association.
    expect(region).toHaveAttribute("aria-labelledby");
    expect(region).toHaveAttribute("aria-readonly", "true");
    const labelId = region.getAttribute("aria-labelledby");
    expect(document.getElementById(labelId)).toHaveTextContent("Sentence to correct");
    // It is static text — never an editable field the learner could submit.
    expect(region.querySelector("textarea")).toBeNull();
    expect(region.querySelector("input")).toBeNull();
  });
});
