import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import AdminSafetyBanner from "./AdminSafetyBanner";

test("renders non-collapsible banner content by default", () => {
  render(
    <AdminSafetyBanner title="Safety contract" testId="safety-banner">
      Banner body copy.
    </AdminSafetyBanner>,
  );

  expect(screen.getByRole("note")).toBeInTheDocument();
  expect(screen.getByText("Safety contract")).toBeVisible();
  expect(screen.getByText("Banner body copy.")).toBeVisible();
  expect(screen.queryByTestId("safety-banner-toggle")).not.toBeInTheDocument();
});

test("toggles collapsible banner content with stable aria controls", () => {
  render(
    <AdminSafetyBanner title="Safety contract" testId="safety-banner" collapsible>
      Banner body copy.
    </AdminSafetyBanner>,
  );

  expect(screen.getByText("Safety contract")).toBeVisible();
  expect(screen.queryByTestId("safety-banner-content")).toBeNull();

  const toggle = screen.getByTestId("safety-banner-toggle");
  expect(toggle).toHaveAttribute("aria-expanded", "false");

  fireEvent.click(toggle);

  const content = screen.getByTestId("safety-banner-content");
  expect(content).toBeVisible();
  expect(content).toHaveTextContent("Banner body copy.");
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  expect(toggle).toHaveAttribute("aria-controls", content.id);

  fireEvent.click(toggle);

  expect(screen.queryByTestId("safety-banner-content")).toBeNull();
  expect(toggle).toHaveAttribute("aria-expanded", "false");
});
