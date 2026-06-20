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

test("toggles mounted collapsible banner content with stable aria controls", () => {
  render(
    <AdminSafetyBanner title="Safety contract" testId="safety-banner" collapsible>
      Banner body copy.
    </AdminSafetyBanner>,
  );

  expect(screen.getByText("Safety contract")).toBeVisible();

  const toggle = screen.getByTestId("safety-banner-toggle");
  const content = screen.getByTestId("safety-banner-content");
  expect(content).not.toBeVisible();
  expect(document.getElementById(toggle.getAttribute("aria-controls"))).toBe(content);
  expect(toggle).toHaveAttribute("aria-expanded", "false");

  fireEvent.click(toggle);

  expect(content).toBeVisible();
  expect(content).toHaveTextContent("Banner body copy.");
  expect(toggle).toHaveAttribute("aria-expanded", "true");

  fireEvent.click(toggle);

  expect(content).not.toBeVisible();
  expect(toggle).toHaveAttribute("aria-expanded", "false");
});

test("uses unique controlled ids for collapsible banners without test ids", () => {
  render(
    <>
      <AdminSafetyBanner title="First banner" collapsible>
        First body copy.
      </AdminSafetyBanner>
      <AdminSafetyBanner title="Second banner" collapsible>
        Second body copy.
      </AdminSafetyBanner>
    </>,
  );

  const toggles = screen.getAllByRole("button");
  const firstControls = toggles[0].getAttribute("aria-controls");
  const secondControls = toggles[1].getAttribute("aria-controls");

  expect(firstControls).toBeTruthy();
  expect(secondControls).toBeTruthy();
  expect(firstControls).not.toBe(secondControls);
});
