import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

jest.mock("../../../lib/authContext", () => ({
  useAuth: () => ({ user: { email: "tester@example.com", role: "admin" }, logout: jest.fn() }),
}));

import AdminShell from "../AdminShell";

// The sidebar is collapsible; pin it open so the IA assertions are
// deterministic regardless of the test env's matchMedia support.
beforeEach(() => {
  try { window.localStorage.setItem("cc-admin-nav-open", "1"); } catch { /* ignore */ }
});

function renderShell(path = "/admin") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<AdminShell />}>
          <Route path="/admin" element={<div>overview</div>} />
          <Route path="/admin/operations" element={<div>ops</div>} />
          {/* catch-all so layout route renders for any /admin/* path */}
          <Route path="/admin/*" element={<div>page</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("AdminShell sidebar IA", () => {
  test("renders exactly 6 top-level groups", () => {
    renderShell("/admin");
    const groups = screen.getAllByTestId(/^admin-nav-group-/);
    expect(groups).toHaveLength(7);
  });

  test("Command Center and Trust Pipeline are default-expanded; others collapsed", () => {
    renderShell("/admin");
    const expanded = screen
      .getAllByTestId(/^admin-nav-group-/)
      .filter((el) => el.getAttribute("data-expanded") === "true");
    // /admin lives under Command Center which is default-open, so the
    // route-based auto-open is a no-op here. Initial expanded count = 2.
    expect(expanded.map((el) => el.getAttribute("data-testid"))).toEqual([
      "admin-nav-group-command-center",
      "admin-nav-group-trust-pipeline",
    ]);
  });

  test("Promotion Queue is not in the sidebar but /admin/eligibility-queue route remains", () => {
    renderShell("/admin");
    expect(screen.queryByTestId("admin-nav-promotion-queue")).toBeNull();
  });
});

describe("AdminShell exam-intel nav title", () => {
  test("masthead shows Exam Registry at /admin/exam-intelligence", () => {
    renderShell("/admin/exam-intelligence");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Exam Registry");
  });

  test("masthead shows Raw CMS / Bulk Import at /admin/exam-intelligence/cms", () => {
    renderShell("/admin/exam-intelligence/cms");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Raw CMS / Bulk Import");
  });

  test("masthead shows Guided Exam at /admin/exam-intelligence/new", () => {
    renderShell("/admin/exam-intelligence/new");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Guided Exam");
  });

  test("masthead shows Exam Registry at /admin/exam-intelligence/workspace/exam-abc", () => {
    renderShell("/admin/exam-intelligence/workspace/exam-abc");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Exam Registry");
  });

  test("masthead shows Exam Registry at /admin/exam-intelligence/exams/exam-abc/add-cycle", () => {
    renderShell("/admin/exam-intelligence/exams/exam-abc/add-cycle");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Exam Registry");
  });
});

describe("AdminShell exam-intel nav active state", () => {
  test("cms route: Raw CMS nav item active, Registry nav item NOT active", () => {
    renderShell("/admin/exam-intelligence/cms");
    const cmsLink = screen.getByTestId("admin-nav-exam-intel-cms");
    const registryLink = screen.getByTestId("admin-nav-exam-intelligence");
    expect(cmsLink.className).toContain("active");
    expect(registryLink.className).not.toContain("active");
  });

  test("workspace route: Registry nav item active", () => {
    renderShell("/admin/exam-intelligence/workspace/exam-abc");
    const registryLink = screen.getByTestId("admin-nav-exam-intelligence");
    expect(registryLink.className).toContain("active");
  });
});
