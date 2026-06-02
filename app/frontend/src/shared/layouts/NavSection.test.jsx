import React from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import { Activity, FileText, LineChart } from "lucide-react";
import NavSection from "./NavSection";

const ITEMS = [
  { to: "/app/study/mocks", label: "Mocks", icon: Activity, testId: "sidebar-mocks" },
  { to: "/app/study/subjects", label: "Subjects", icon: LineChart, testId: "sidebar-subjects" },
];

const ITEMS_END = [
  { to: "/app/study", label: "Home", icon: FileText, testId: "sidebar-study-home", end: true },
  { to: "/app/study/mocks", label: "Mocks", icon: Activity, testId: "sidebar-mocks2" },
];

function renderSection(path, items = ITEMS) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <NavSection
        label="Learning"
        items={items}
        collapsible
        defaultOpen={false}
        testId="section-learning"
      />
    </MemoryRouter>,
  );
}

test("section starts collapsed when defaultOpen=false", () => {
  renderSection("/app/today");
  expect(screen.queryByTestId("sidebar-mocks")).toBeNull();
});

test("auto-opens when a child route matches on initial render", () => {
  renderSection("/app/study/mocks");
  expect(screen.getByTestId("sidebar-mocks")).toBeTruthy();
});

test("auto-opens on nested child route (prefix match)", () => {
  renderSection("/app/study/subjects/biology");
  expect(screen.getByTestId("sidebar-subjects")).toBeTruthy();
});

test("end:true items only match exact path", () => {
  // /app/study/mocks does NOT match the end:true /app/study item
  renderSection("/app/study/mocks", ITEMS_END);
  // Mocks (non-end) should cause auto-open; Home (end) alone would not match /app/study/mocks
  expect(screen.getByTestId("sidebar-mocks2")).toBeTruthy();
});

test("end:true item matches exactly /app/study", () => {
  renderSection("/app/study", ITEMS_END);
  expect(screen.getByTestId("sidebar-study-home")).toBeTruthy();
});

test("manual collapse is not overridden without navigation", () => {
  renderSection("/app/study/mocks");
  // Section should be open because child matched
  expect(screen.getByTestId("sidebar-mocks")).toBeTruthy();
  // User manually collapses
  fireEvent.click(screen.getByTestId("section-learning"));
  expect(screen.queryByTestId("sidebar-mocks")).toBeNull();
});
