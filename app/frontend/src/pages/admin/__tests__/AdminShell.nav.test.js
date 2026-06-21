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
  test("renders exactly 7 top-level groups", () => {
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

describe("AdminShell exam-intel nav title (I8-A)", () => {
  test("masthead shows Exam Management at /admin/exam-intelligence", () => {
    renderShell("/admin/exam-intelligence");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Exam Management");
  });

  test("masthead shows Exam Management at /admin/exam-intelligence/console (no dedicated nav entry)", () => {
    renderShell("/admin/exam-intelligence/console");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Exam Management");
  });

  test("masthead shows Exam Management at /admin/exam-intelligence/cms (no dedicated nav entry)", () => {
    renderShell("/admin/exam-intelligence/cms");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Exam Management");
  });

  test("masthead shows Exam Management at /admin/exam-intelligence/new (no dedicated nav entry)", () => {
    renderShell("/admin/exam-intelligence/new");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Exam Management");
  });

  test("masthead shows Exam Management at /admin/exam-intelligence/workspace/exam-abc", () => {
    renderShell("/admin/exam-intelligence/workspace/exam-abc");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Exam Management");
  });

  test("masthead shows Exam Management at /admin/exam-intelligence/exams/exam-abc", () => {
    renderShell("/admin/exam-intelligence/exams/exam-abc");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Exam Management");
  });

  test("masthead shows Exam Management at /admin/exam-intelligence/exams/exam-abc/add-cycle", () => {
    renderShell("/admin/exam-intelligence/exams/exam-abc/add-cycle");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Exam Management");
  });
});

describe("AdminShell exam-intel nav active state (I8-A)", () => {
  test("Exam Management nav item is active at /admin/exam-intelligence", () => {
    renderShell("/admin/exam-intelligence");
    const link = screen.getByTestId("admin-nav-exam-management");
    expect(link.className).toContain("active");
  });

  test("Exam Management nav item is active at /admin/exam-intelligence/workspace/exam-abc", () => {
    renderShell("/admin/exam-intelligence/workspace/exam-abc");
    const link = screen.getByTestId("admin-nav-exam-management");
    expect(link.className).toContain("active");
  });

  test("Exam Management nav item is active at /admin/exam-intelligence/console", () => {
    renderShell("/admin/exam-intelligence/console");
    const link = screen.getByTestId("admin-nav-exam-management");
    expect(link.className).toContain("active");
  });

  test("Exam Management nav item is active at /admin/exam-intelligence/exams/exam-abc", () => {
    renderShell("/admin/exam-intelligence/exams/exam-abc");
    const link = screen.getByTestId("admin-nav-exam-management");
    expect(link.className).toContain("active");
  });
});

describe("I8-A — Exam Management nav consolidation", () => {
  test("single Exam Management entry routes to /admin/exam-intelligence", () => {
    renderShell("/admin/exam-intelligence");
    const link = screen.getByTestId("admin-nav-exam-management");
    expect(link.getAttribute("href")).toBe("/admin/exam-intelligence");
    expect(link.textContent).toContain("Exam Management");
  });

  test("Exam Governance Console is NOT a visible nav link", () => {
    renderShell("/admin/exam-intelligence");
    expect(screen.queryByTestId("admin-nav-exam-governance-console")).toBeNull();
  });

  test("Exam Registry is NOT a visible nav link", () => {
    renderShell("/admin/exam-intelligence");
    expect(screen.queryByTestId("admin-nav-exam-intelligence")).toBeNull();
  });

  test("Create exam is NOT a visible nav link", () => {
    renderShell("/admin/exam-intelligence");
    expect(screen.queryByTestId("admin-nav-guided-exam-wizard")).toBeNull();
  });

  test("Advanced Import / Repair is NOT a visible nav link", () => {
    renderShell("/admin/exam-intelligence");
    expect(screen.queryByTestId("admin-nav-exam-intel-cms")).toBeNull();
  });

  test("the Advanced affordance is NOT rendered", () => {
    renderShell("/admin/exam-intelligence");
    expect(screen.queryByTestId("admin-nav-exam-advanced")).toBeNull();
  });

  test("the four KG lanes are present with correct labels", () => {
    renderShell("/admin/exam-intelligence");
    expect(screen.getByTestId("admin-nav-kg-landing")).toBeTruthy();
    ["Exam truth & planner readiness",
     "User eligibility truth",
     "Official-source trust & change propagation",
     "AI + personalization guardrails"].forEach((label) => {
      expect(screen.getByText(label)).toBeTruthy();
    });
    // Lane 2-4 representative entries untouched.
    expect(screen.getByTestId("admin-nav-exam-eligibility")).toBeTruthy();
    expect(screen.getByTestId("admin-nav-organizations")).toBeTruthy();
    expect(screen.getByTestId("admin-nav-ai-policy")).toBeTruthy();
  });
});
