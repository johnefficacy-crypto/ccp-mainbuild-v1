import { render, screen } from "@testing-library/react";
import WordChips from "./WordChips";

describe("WordChips", () => {
  test("renders nothing when there are no required words", () => {
    const { container } = render(<WordChips requiredWords={[]} text="anything" />);
    expect(container.firstChild).toBeNull();
  });

  test("shows a chip per required word and a words-used counter", () => {
    render(<WordChips requiredWords={["diligent", "scholar"]} text="" />);
    expect(screen.getAllByTestId(/^word-chip$/)).toHaveLength(2);
    expect(screen.getByTestId("words-used")).toHaveTextContent("0/2");
  });

  test("marks used words and updates the N/total counter", () => {
    render(<WordChips requiredWords={["diligent", "scholar"]} text="A diligent mind." />);
    expect(screen.getAllByTestId("word-chip-used")).toHaveLength(1);
    expect(screen.getByTestId("words-used")).toHaveTextContent("1/2");
  });

  test("tracks each unit independently (no shared state across instances)", () => {
    const { rerender } = render(<WordChips requiredWords={["ran"]} text="he ran" />);
    expect(screen.getByTestId("words-used")).toHaveTextContent("1/1");
    rerender(<WordChips requiredWords={["ran"]} text="he walked" />);
    expect(screen.getByTestId("words-used")).toHaveTextContent("0/1");
  });
});
