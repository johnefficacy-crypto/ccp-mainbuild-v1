import React from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";

import PrePlanCalibration from "../PrePlanCalibration";

const REQUIRED = [
  { subject_id: "s-quant", subject_name: "Quantitative Aptitude" },
  { subject_id: "s-reason", subject_name: "Reasoning" },
];

function renderCalibration(props = {}) {
  const onSubmit = jest.fn();
  const onSkip = jest.fn();
  const utils = render(
    <PrePlanCalibration
      requiredSubjects={REQUIRED}
      items={[]}
      attemptsUsed={null}
      onSubmit={onSubmit}
      onSkip={onSkip}
      saving={false}
      error={null}
      {...props}
    />,
  );
  return { onSubmit, onSkip, ...utils };
}

// Find the band button for a given subject card by walking up to the card and
// scoping the query — band labels repeat across cards.
function bandButton(subjectName, bandLabel) {
  const heading = screen.getByText(subjectName);
  const card = heading.parentElement;
  return within(card).getByRole("button", { name: bandLabel });
}

test("Save & continue is disabled until every subject is banded AND attempts chosen", () => {
  renderCalibration();
  const saveBtn = screen.getByTestId("calibration-save-btn");
  expect(saveBtn).toBeDisabled();

  // Answer only the first subject — still incomplete.
  fireEvent.click(bandButton("Quantitative Aptitude", "Strong"));
  expect(saveBtn).toBeDisabled();
  expect(screen.getByTestId("calibration-helper").textContent).toMatch(
    /Answer all 2 subjects/i,
  );

  // Answer the second subject — all banded, but attempts still unselected so
  // Save stays disabled and the helper now asks for the attempt count.
  fireEvent.click(bandButton("Reasoning", "Weak"));
  expect(saveBtn).toBeDisabled();
  expect(screen.getByTestId("calibration-helper").textContent).toMatch(
    /how many times you've attempted/i,
  );

  // Choose an attempts option — now complete and enabled, helper gone.
  fireEvent.click(screen.getByRole("button", { name: /First attempt/i }));
  expect(saveBtn).not.toBeDisabled();
  expect(screen.queryByTestId("calibration-helper")).toBeNull();
});

test("attempts is required: all subjects banded but no attempts keeps Save disabled", () => {
  // Prefill bands via items but leave attempts unselected (null).
  const { onSubmit } = renderCalibration({
    items: [
      { subject_id: "s-quant", band: "strong" },
      { subject_id: "s-reason", band: "weak" },
    ],
  });
  const saveBtn = screen.getByTestId("calibration-save-btn");
  expect(saveBtn).toBeDisabled();

  // Choosing an attempts option enables Save and onSubmit gets the chosen value.
  fireEvent.click(screen.getByRole("button", { name: /1 attempt/i }));
  expect(saveBtn).not.toBeDisabled();

  fireEvent.click(saveBtn);
  expect(onSubmit).toHaveBeenCalledTimes(1);
  expect(onSubmit.mock.calls[0][1]).toBe(1);
});

test("existing items prefill the band selections (saved band renders pressed)", () => {
  renderCalibration({
    items: [
      { subject_id: "s-quant", subject_name: "Quantitative Aptitude", band: "decent" },
      { subject_id: "s-reason", subject_name: "Reasoning", band: "strong" },
    ],
    // A saved attempts value also prefills (editing flow), so an already
    // calibrated user sees Save enabled without re-touching anything.
    attemptsUsed: 2,
  });

  // Both bands and attempts prefilled → save is immediately enabled.
  expect(screen.getByTestId("calibration-save-btn")).not.toBeDisabled();

  // The saved bands render with aria-pressed=true on the right buttons.
  expect(bandButton("Quantitative Aptitude", "Decent")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(bandButton("Reasoning", "Strong")).toHaveAttribute("aria-pressed", "true");
  // A non-selected band stays unpressed.
  expect(bandButton("Quantitative Aptitude", "Weak")).toHaveAttribute(
    "aria-pressed",
    "false",
  );
});

test("clicking Skip for now calls onSkip", () => {
  const { onSkip } = renderCalibration();
  fireEvent.click(screen.getByRole("button", { name: /Skip for now/i }));
  expect(onSkip).toHaveBeenCalledTimes(1);
});

test("submitting calls onSubmit with bands for every subject plus attempts", () => {
  const { onSubmit } = renderCalibration();

  fireEvent.click(bandButton("Quantitative Aptitude", "Strong"));
  fireEvent.click(bandButton("Reasoning", "Weak"));
  // Pick a non-default attempts value.
  fireEvent.click(screen.getByRole("button", { name: /2\+ attempts/i }));

  fireEvent.click(screen.getByTestId("calibration-save-btn"));

  expect(onSubmit).toHaveBeenCalledTimes(1);
  const [bands, attempts] = onSubmit.mock.calls[0];
  expect(attempts).toBe(2);
  expect(bands).toEqual(
    expect.arrayContaining([
      { subject_id: "s-quant", band: "strong" },
      { subject_id: "s-reason", band: "weak" },
    ]),
  );
  expect(bands).toHaveLength(2);
});

test("the error prop renders an inline error message", () => {
  renderCalibration({ error: "Couldn't save your answers. Try again." });
  const banner = screen.getByTestId("calibration-error");
  expect(banner).toHaveTextContent("Couldn't save your answers. Try again.");
  expect(banner).toHaveAttribute("role", "alert");
});

test("Save shows a saving state and is disabled while saving", () => {
  renderCalibration({
    saving: true,
    items: [
      { subject_id: "s-quant", band: "strong" },
      { subject_id: "s-reason", band: "weak" },
    ],
  });
  const saveBtn = screen.getByTestId("calibration-save-btn");
  expect(saveBtn).toBeDisabled();
  expect(saveBtn.textContent).toMatch(/Saving/i);
});

test("with no required subjects it shows an explicit empty state, not a perpetual loader", () => {
  const { onSkip } = renderCalibration({ requiredSubjects: [] });

  // The empty state replaces the old indefinite "Loading subjects…" message so
  // the panel can never hang when the required set is empty.
  expect(screen.getByTestId("calibration-empty")).toHaveTextContent(
    /No subjects to calibrate/i,
  );
  expect(screen.queryByText(/Loading subjects/i)).toBeNull();

  // Skip stays available so the user can close out of the empty panel, and
  // Save is disabled (nothing to submit).
  expect(screen.getByTestId("calibration-save-btn")).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: /Skip for now/i }));
  expect(onSkip).toHaveBeenCalledTimes(1);
});
