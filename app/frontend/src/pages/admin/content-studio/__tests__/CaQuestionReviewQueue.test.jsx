import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import CaQuestionReviewQueue from "../CaQuestionReviewQueue";
import { contentStudioApi as mockApi } from "../contentStudioApi";

// ── mock hooks ──────────────────────────────────────────────────────────────
let mockCollection;
let mockRun;
jest.mock("../../../../lib/hooks/useApiCollection", () => ({
  __esModule: true,
  default: () => mockCollection,
}));
jest.mock("../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({ run: (...a) => mockRun(...a), busy: false }),
}));

// ── mock the API layer (keep the real transitions map) ──────────────────────
// The factory uses only jest.fn (no out-of-scope refs); tests reach the same fns
// through the imported (mocked) `contentStudioApi as mockApi` binding.
jest.mock("../contentStudioApi", () => ({
  __esModule: true,
  contentStudioApi: {
    listCaCandidates: jest.fn(),
    getCaCandidate: jest.fn(),
    reviewCaCandidate: jest.fn(() => Promise.resolve({})),
    promoteCaCandidate: jest.fn(() => Promise.resolve({})),
  },
  CA_REVIEW_TRANSITIONS: {
    review_ready: ["approved", "rejected"],
    approved: ["rejected", "review_ready"],
    rejected: ["review_ready"],
  },
}));

const CAND = "cand-1";

function snapshot(status = "review_ready") {
  return {
    candidate: {
      id: CAND, status,
      question_payload: {
        stem: "Which body issued the June 2026 circular?",
        options: [{ id: "a", text: "RBI" }, { id: "b", text: "SEBI" },
                  { id: "c", text: "IRDAI" }, { id: "d", text: "PFRDA" }],
        correct_option_id: "a", explanation: "RBI per the claim.",
      },
      validation_result: { ok: true }, verifier_verdict: { supported_answer: true },
    },
    event: { id: "ev-1", canonical_title: "RBI circular" }, claims: [{ id: "c1" }],
    generation_runs: [],
  };
}

beforeEach(() => {
  mockRun = jest.fn(async (thunk) => { await thunk(); return { error: null }; });
  mockCollection = {
    items: [{ id: CAND, status: "review_ready", validation_result: { ok: true },
              question_payload: { stem: "Which body issued the June 2026 circular?" } }],
    status: "ready", total: 1, refresh: jest.fn(),
  };
  mockApi.listCaCandidates.mockReset().mockResolvedValue({ items: [], total: 0 });
  mockApi.getCaCandidate.mockReset().mockResolvedValue(snapshot("review_ready"));
  mockApi.reviewCaCandidate.mockClear();
  mockApi.promoteCaCandidate.mockClear();
});

const PERMS = { canReview: true, canPublish: false };

test("lists candidates and opens the review drill-in", async () => {
  render(<CaQuestionReviewQueue perms={PERMS} />);
  expect(screen.getByTestId("ca-question-review-queue")).toBeInTheDocument();
  fireEvent.click(screen.getByTestId(`ca-review-open-${CAND}`));
  await waitFor(() => expect(mockApi.getCaCandidate).toHaveBeenCalledWith(CAND));
  expect(await screen.findByTestId("ca-review-stem")).toHaveTextContent("June 2026 circular");
});

test("approve submits reviewCaCandidate with CAS expected_status", async () => {
  render(<CaQuestionReviewQueue perms={PERMS} />);
  fireEvent.click(screen.getByTestId(`ca-review-open-${CAND}`));
  await screen.findByTestId("ca-review-decision");
  fireEvent.change(screen.getByTestId("ca-review-decision"), { target: { value: "approved" } });
  fireEvent.click(screen.getByTestId("ca-review-submit"));
  await waitFor(() =>
    expect(mockApi.reviewCaCandidate).toHaveBeenCalledWith(CAND, {
      status: "approved", expected_status: "review_ready", reviewer_notes: undefined,
    })
  );
});

test("promote affordance hidden without publish permission", async () => {
  mockApi.getCaCandidate.mockResolvedValue(snapshot("approved"));
  render(<CaQuestionReviewQueue perms={{ canReview: true, canPublish: false }} />);
  fireEvent.click(screen.getByTestId(`ca-review-open-${CAND}`));
  await screen.findByTestId("ca-review-dialog");
  expect(screen.queryByTestId("ca-review-promote")).not.toBeInTheDocument();
});

test("promote calls promoteCaCandidate when publish-permitted", async () => {
  mockApi.getCaCandidate.mockResolvedValue(snapshot("approved"));
  render(<CaQuestionReviewQueue perms={{ canReview: true, canPublish: true }} />);
  fireEvent.click(screen.getByTestId(`ca-review-open-${CAND}`));
  const btn = await screen.findByTestId("ca-review-promote");
  fireEvent.click(btn);
  await waitFor(() =>
    expect(mockApi.promoteCaCandidate).toHaveBeenCalledWith(CAND, { expected_status: "approved" })
  );
});
