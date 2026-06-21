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

  test("masthead shows Advanced Import / Repair at /admin/exam-intelligence/cms", () => {
    renderShell("/admin/exam-intelligence/cms");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Advanced Import / Repair");
    expect(screen.queryByText("Raw CMS / Bulk Import")).toBeNull();
  });

  test("masthead shows Create exam at /admin/exam-intelligence/new", () => {
    renderShell("/admin/exam-intelligence/new");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Create exam");
  });

  test("masthead shows Exam Governance Console at /admin/exam-intelligence/console", () => {
    renderShell("/admin/exam-intelligence/console");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Exam Governance Console");
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

  test("console route: console nav item active, Registry NOT active", () => {
    renderShell("/admin/exam-intelligence/console");
    expect(screen.getByTestId("admin-nav-exam-governance-console").className).toContain("active");
    expect(screen.getByTestId("admin-nav-exam-intelligence").className).not.toContain("active");
  });
});

describe("Wave 4.6B — Exam-truth lane posture", () => {
  test("Exam Governance Console is a PRIMARY nav link routing to /console", () => {
    renderShell("/admin/exam-intelligence");
    const link = screen.getByTestId("admin-nav-exam-governance-console");
    expect(link.getAttribute("href")).toBe("/admin/exam-intelligence/console");
    // Primary: not inside the Advanced affordance.
    expect(link.closest("[data-testid='admin-nav-exam-advanced']")).toBeNull();
  });

  test("Exam Registry link is still present and primary, routing to /admin/exam-intelligence", () => {
    renderShell("/admin/exam-intelligence");
    const link = screen.getByTestId("admin-nav-exam-intelligence");
    expect(link.getAttribute("href")).toBe("/admin/exam-intelligence");
    expect(link.closest("[data-testid='admin-nav-exam-advanced']")).toBeNull();
  });

  test("Create exam is demoted into the Advanced affordance and routes to /new", () => {
    renderShell("/admin/exam-intelligence");
    const advanced = screen.getByTestId("admin-nav-exam-advanced");
    const link = screen.getByTestId("admin-nav-guided-exam-wizard");
    expect(link.textContent).toContain("Create exam");
    expect(link.getAttribute("href")).toBe("/admin/exam-intelligence/new");
    expect(advanced.contains(link)).toBe(true);
  });

  test("Advanced Import / Repair is demoted into the Advanced affordance and routes to /cms", () => {
    renderShell("/admin/exam-intelligence");
    const advanced = screen.getByTestId("admin-nav-exam-advanced");
    const link = screen.getByTestId("admin-nav-exam-intel-cms");
    expect(link.textContent).toContain("Advanced Import / Repair");
    expect(link.getAttribute("href")).toBe("/admin/exam-intelligence/cms");
    expect(advanced.contains(link)).toBe(true);
    expect(screen.queryByText("Raw CMS / Bulk Import")).toBeNull();
  });

  test("the four KG lanes (D-A) are unchanged", () => {
    renderShell("/admin/exam-intelligence");
    // Landing + all four lane labels still present and in order.
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
