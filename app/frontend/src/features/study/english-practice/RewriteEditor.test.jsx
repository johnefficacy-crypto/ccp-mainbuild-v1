import { render, screen, fireEvent, within } from "@testing-library/react";
import RewriteEditor from "./RewriteEditor";

describe("RewriteEditor", () => {
  test("prefilled with previousAnswer", () => {
    render(<RewriteEditor previousAnswer="the cat sat" onSubmit={() => {}} />);
    expect(screen.getByTestId("rewrite-input")).toHaveValue("the cat sat");
  });

  test("editing updates the embedded diff with emerald styling", () => {
    render(<RewriteEditor previousAnswer="the cat sat" onSubmit={() => {}} />);
    fireEvent.change(screen.getByTestId("rewrite-input"), {
      target: { value: "the big cat sat" },
    });
    const diff = screen.getByTestId("before-after-diff");
    const added = within(diff).getByText("big");
    expect(added).toHaveClass("bg-emerald-100", "text-emerald-800");
  });

  test("submit calls onSubmit with the edited text", () => {
    const onSubmit = jest.fn();
    render(<RewriteEditor previousAnswer="old text" onSubmit={onSubmit} />);
    fireEvent.change(screen.getByTestId("rewrite-input"), {
      target: { value: "  new rewrite  " },
    });
    fireEvent.click(screen.getByTestId("rewrite-submit"));
    expect(onSubmit).toHaveBeenCalledWith("new rewrite");
  });

  test("submit disabled when busy", () => {
    render(
      <RewriteEditor previousAnswer="text" busy onSubmit={() => {}} />
    );
    expect(screen.getByTestId("rewrite-submit")).toBeDisabled();
  });
});
