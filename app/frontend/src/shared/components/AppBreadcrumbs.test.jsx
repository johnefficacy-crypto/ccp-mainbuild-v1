import React from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import AppBreadcrumbs from "./AppBreadcrumbs";
import { BreadcrumbLeafProvider } from "../navigation/BreadcrumbLeafContext";

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <BreadcrumbLeafProvider>
        <AppBreadcrumbs />
      </BreadcrumbLeafProvider>
    </MemoryRouter>,
  );
}

test("renders nothing on a shallow route /app/today", () => {
  const { container } = renderAt("/app/today");
  expect(container.firstChild).toBeNull();
});

test("renders nothing on another shallow route /app/study", () => {
  const { container } = renderAt("/app/study");
  expect(container.firstChild).toBeNull();
});

test("mock result trail: Study / Mocks / Result with correct links and aria-current", () => {
  renderAt("/app/study/mocks/attempts/abc/result");
  expect(screen.getByText("Study")).toBeTruthy();
  expect(screen.getByText("Mocks")).toBeTruthy();
  const leaf = screen.getByText("Result");
  expect(leaf).toBeTruthy();
  expect(leaf.closest("[aria-current='page']")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Study" }).getAttribute("href")).toBe("/app/study");
  expect(screen.getByRole("link", { name: "Mocks" }).getAttribute("href")).toBe("/app/study/mocks");
});

test("mock review trail renders Review as leaf with aria-current", () => {
  renderAt("/app/study/mocks/attempts/xyz/review");
  const leaf = screen.getByText("Review");
  expect(leaf.closest("[aria-current='page']")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Study" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "Mocks" })).toBeTruthy();
});

test("exam detail without leaf context renders fallback 'Exam'", () => {
  renderAt("/app/eligibility/exams/upsc-cse");
  expect(screen.getByText("Exam")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Eligibility" }).getAttribute("href")).toBe("/app/eligibility");
  expect(screen.getByRole("link", { name: "Exams" }).getAttribute("href")).toBe("/app/eligibility/exams");
});

test("marketplace detail trail", () => {
  renderAt("/app/marketplace/course-123");
  expect(screen.getByRole("link", { name: "Marketplace" })).toBeTruthy();
  expect(screen.getByText("Detail").closest("[aria-current='page']")).toBeTruthy();
});

test("marketplace learn trail has Detail link pointing to parent path", () => {
  renderAt("/app/marketplace/course-123/learn");
  expect(screen.getByRole("link", { name: "Marketplace" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "Detail" }).getAttribute("href")).toBe("/app/marketplace/course-123");
  expect(screen.getByText("Learn").closest("[aria-current='page']")).toBeTruthy();
});

test("notifications preferences trail", () => {
  renderAt("/app/notifications/preferences");
  expect(screen.getByRole("link", { name: "Notifications" })).toBeTruthy();
  expect(screen.getByText("Preferences").closest("[aria-current='page']")).toBeTruthy();
});

test("mentors detail trail", () => {
  renderAt("/app/mentors/some-mentor");
  expect(screen.getByRole("link", { name: "Mentors" })).toBeTruthy();
  expect(screen.getByText("Detail").closest("[aria-current='page']")).toBeTruthy();
});

test("renders nothing on bare community space route with no leaf override", () => {
  const { container } = renderAt("/app/community/foo");
  expect(container.firstChild).toBeNull();
});

test("community channel trail renders Community and Space ancestors", () => {
  renderAt("/app/community/upsc/general");
  expect(screen.getByRole("link", { name: "Community" }).getAttribute("href")).toBe("/app/community");
  expect(screen.getByRole("link", { name: "Space" }).getAttribute("href")).toBe("/app/community/upsc");
  expect(screen.getByText("Channel").closest("[aria-current='page']")).toBeTruthy();
});
