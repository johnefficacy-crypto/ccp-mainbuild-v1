/**
 * Legacy Mock Content → Content Studio redirect: proves the query params
 * (filters, pagination) survive the redirect, not just the path. A landing
 * route echoes the resolved search string so we assert the real navigation
 * target, using the actual MockContentRedirect component.
 */
import React from "react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import MockContentRedirect from "./mockContentRedirect";

function StudioLanding() {
  const { search } = useLocation();
  return <div data-testid="studio" data-search={search} />;
}

function renderAt(path, tab) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/mocks/questions" element={<MockContentRedirect tab={tab} />} />
        <Route path="/admin/mocks/review-queue" element={<MockContentRedirect tab={tab} />} />
        <Route path="/admin/content-studio" element={<StudioLanding />} />
      </Routes>
    </MemoryRouter>,
  );
  return new URLSearchParams(screen.getByTestId("studio").getAttribute("data-search"));
}

test("carries filters + pagination through the library redirect", () => {
  const params = renderAt("/admin/mocks/questions?status=draft&page=2", "library");
  expect(params.get("tab")).toBe("library");
  expect(params.get("type")).toBe("objective_question");
  expect(params.get("status")).toBe("draft");
  expect(params.get("page")).toBe("2");
});

test("maps the review-queue legacy route to its tab, params intact", () => {
  const params = renderAt("/admin/mocks/review-queue?page=3", "review-queue");
  expect(params.get("tab")).toBe("review-queue");
  expect(params.get("type")).toBe("objective_question");
  expect(params.get("page")).toBe("3");
});
