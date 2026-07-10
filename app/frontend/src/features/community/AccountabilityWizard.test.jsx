import React from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import AccountabilityWizard from "./AccountabilityWizard";

const KEY = "cc.accountability.prefs";

function renderWizard(url = "/app/accountability?exam=upsc-cse") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <AccountabilityWizard />
    </MemoryRouter>,
  );
}

beforeEach(() => window.localStorage.clear());
afterEach(() => window.localStorage.clear());

test("prefills exam from ?exam=, saves durably, and shows honest not-live copy", () => {
  renderWizard();
  expect(screen.getByTestId("wizard-exam").value).toBe("upsc-cse");
  fireEvent.change(screen.getByTestId("wizard-stage"), { target: { value: "Revision" } });
  fireEvent.click(screen.getByTestId("accountability-wizard-submit"));

  const done = screen.getByTestId("accountability-wizard-done");
  expect(done.textContent).toContain("upsc-cse");
  // Honest: durable device-local save + explicitly not live yet.
  expect(done.textContent).toContain("Saved on this device");
  expect(done.textContent.toLowerCase()).toContain("isn't live yet");
  // Must NOT claim a server-side pool membership it can't back up.
  expect(done.textContent.toLowerCase()).not.toContain("on the accountability pool");

  // Preferences are actually persisted.
  const stored = JSON.parse(window.localStorage.getItem(KEY));
  expect(stored.exam).toBe("upsc-cse");
  expect(stored.stage).toBe("Revision");
});

test("does not dead-end — the confirmation can return to editing", () => {
  renderWizard();
  fireEvent.click(screen.getByTestId("accountability-wizard-submit"));
  expect(screen.getByTestId("accountability-wizard-done")).toBeTruthy();
  fireEvent.click(screen.getByTestId("accountability-wizard-restart"));
  expect(screen.getByTestId("accountability-wizard")).toBeTruthy();
});

test("restores previously saved preferences on a fresh mount", () => {
  window.localStorage.setItem(
    KEY,
    JSON.stringify({ exam: "ssc-cgl", stage: "Final stretch", checkin: "Evening" }),
  );
  renderWizard("/app/accountability"); // no ?exam= — falls back to saved
  expect(screen.getByTestId("wizard-exam").value).toBe("ssc-cgl");
  expect(screen.getByTestId("wizard-stage").value).toBe("Final stretch");
});

test("works with no exam param and no prior prefs", () => {
  renderWizard("/app/accountability");
  expect(screen.getByTestId("wizard-exam").value).toBe("");
  fireEvent.click(screen.getByTestId("accountability-wizard-submit"));
  expect(screen.getByTestId("accountability-wizard-done")).toBeTruthy();
});
