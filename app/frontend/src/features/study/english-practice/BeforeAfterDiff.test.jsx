import { render, screen } from "@testing-library/react";
import BeforeAfterDiff from "./BeforeAfterDiff";

describe("BeforeAfterDiff", () => {
  test("added word gets emerald styling in the Rewrite block", () => {
    render(<BeforeAfterDiff before="the cat sat" after="the big cat sat" />);
    const added = screen.getByText("big");
    expect(added).toHaveClass("bg-emerald-100", "text-emerald-800");
  });

  test("removed word is struck through in the Previous block", () => {
    render(<BeforeAfterDiff before="the cat ran" after="the cat" />);
    const removed = screen.getByText("ran");
    expect(removed).toHaveClass("line-through", "text-rose-600");
  });

  test("identical strings produce no added or removed styling", () => {
    const { container } = render(
      <BeforeAfterDiff before="the cat sat" after="the cat sat" />
    );
    expect(container.querySelector(".line-through")).toBeNull();
    expect(container.querySelector(".bg-emerald-100")).toBeNull();
  });
});
