import React from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import AccountabilityWizard from "./AccountabilityWizard";

function renderWizard(url = "/app/accountability?exam=upsc-cse") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <AccountabilityWizard />
    </MemoryRouter>,
  );
}

test("prefills the target exam from ?exam= and completes to the pool confirmation", () => {
  renderWizard();
  expect(screen.getByTestId("wizard-exam").value).toBe("upsc-cse");
  fireEvent.click(screen.getByTestId("accountability-wizard-submit"));
  const done = screen.getByTestId("accountability-wizard-done");
  expect(done).toBeTruthy();
  expect(done.textContent).toContain("upsc-cse");
});

test("does not dead-end — the confirmation can return to editing", () => {
  renderWizard();
  fireEvent.click(screen.getByTestId("accountability-wizard-submit"));
  expect(screen.getByTestId("accountability-wizard-done")).toBeTruthy();
  fireEvent.click(screen.getByTestId("accountability-wizard-restart"));
  expect(screen.getByTestId("accountability-wizard")).toBeTruthy();
});

test("works with no exam param", () => {
  renderWizard("/app/accountability");
  expect(screen.getByTestId("wizard-exam").value).toBe("");
  fireEvent.click(screen.getByTestId("accountability-wizard-submit"));
  expect(screen.getByTestId("accountability-wizard-done")).toBeTruthy();
});
