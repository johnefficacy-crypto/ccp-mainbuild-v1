import { render, screen, fireEvent, within, waitFor } from "@testing-library/react";
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

  test("submit disabled when the rewrite is unchanged from the previous answer", () => {
    render(<RewriteEditor previousAnswer="the cat sat" onSubmit={() => {}} />);
    // Untouched — identical to the previous answer.
    expect(screen.getByTestId("rewrite-submit")).toBeDisabled();
    // Whitespace-only changes still count as unchanged.
    fireEvent.change(screen.getByTestId("rewrite-input"), {
      target: { value: "  the cat sat  " },
    });
    expect(screen.getByTestId("rewrite-submit")).toBeDisabled();
    expect(screen.getByTestId("rewrite-unchanged")).toBeInTheDocument();
    // A real edit re-enables submit.
    fireEvent.change(screen.getByTestId("rewrite-input"), {
      target: { value: "the cat sat quietly" },
    });
    expect(screen.getByTestId("rewrite-submit")).not.toBeDisabled();
  });

  describe("autosave", () => {
    beforeEach(() => window.sessionStorage.clear());

    test("restores an in-progress rewrite over the server answer", () => {
      window.sessionStorage.setItem("ewp:draft:S1:1", "my saved correction");
      render(
        <RewriteEditor previousAnswer="server answer" sessionId="S1" unitNumber={1} onSubmit={() => {}} />,
      );
      expect(screen.getByTestId("rewrite-input")).toHaveValue("my saved correction");
    });

    test("seeds from the previous answer when there is no saved draft", () => {
      render(
        <RewriteEditor previousAnswer="server answer" sessionId="S1" unitNumber={1} onSubmit={() => {}} />,
      );
      expect(screen.getByTestId("rewrite-input")).toHaveValue("server answer");
    });

    test("clears the draft only after a successful rewrite; preserves it on failure", async () => {
      const ok = jest.fn().mockResolvedValue({ ok: true });
      const { unmount } = render(
        <RewriteEditor previousAnswer="old" sessionId="S1" unitNumber={1} onSubmit={ok} />,
      );
      fireEvent.change(screen.getByTestId("rewrite-input"), { target: { value: "new correction" } });
      expect(window.sessionStorage.getItem("ewp:draft:S1:1")).toBe("new correction");
      fireEvent.click(screen.getByTestId("rewrite-submit"));
      await waitFor(() => expect(window.sessionStorage.getItem("ewp:draft:S1:1")).toBeNull());
      unmount();

      const fail = jest.fn().mockResolvedValue({ ok: false });
      render(<RewriteEditor previousAnswer="old" sessionId="S1" unitNumber={1} onSubmit={fail} />);
      fireEvent.change(screen.getByTestId("rewrite-input"), { target: { value: "keep this" } });
      fireEvent.click(screen.getByTestId("rewrite-submit"));
      await waitFor(() => expect(fail).toHaveBeenCalled());
      expect(window.sessionStorage.getItem("ewp:draft:S1:1")).toBe("keep this");
    });
  });
});
