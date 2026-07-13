import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import CaQuestionReviewQueue from "../CaQuestionReviewQueue";
import { contentStudioApi as mockApi } from "../contentStudioApi";

// ── mock hooks with their REAL contracts (checkpost #970 F1) ────────────────
// useApiCollection(url, seed, { params }); useApiAction().run({ action, ... }).
let collectionArgs;
let mockCollection;
jest.mock("../../../../lib/hooks/useApiCollection", () => ({
  __esModule: true,
  default: (url, seed, options) => {
    collectionArgs = { url, seed, options };
    return mockCollection;
  },
}));
let lastAction;
jest.mock("../../../../lib/hooks/useApiAction", () => ({
  __esModule: true,
  default: () => ({
    run: async ({ action }) => {
      lastAction = action;
      await action();
      return { ok: true };
    },
    busy: false,
  }),
}));

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
  isValidReason: (r) => (r || "").trim().length >= 8 && (r || "").trim().length <= 500,
}));

const CAND = "cand-1";
const TOKEN = "2026-07-12T10:00:00Z";

function envelope(status = "review_ready") {
  return {
    candidate: {
      id: CAND, status, updated_at: TOKEN,
      question_payload: {
        stem: "Which body issued the June 2026 circular?",
        options: [{ id: "a", text: "RBI" }, { id: "b", text: "SEBI" },
                  { id: "c", text: "IRDAI" }, { id: "d", text: "PFRDA" }],
        correct_option_id: "a", explanation: "RBI per the claim.",
      },
      validation_result: { ok: true }, verifier_verdict: { supported_answer: true },
    },
    event: { id: "ev-1", canonical_title: "RBI circular", relevance_until: "2026-09-01" },
    claims: [{ id: "c1", claim_text: "RBI issued a circular.", factual_status: "current",
               evidence: [{ evidence_text: "RBI...", source: { name: "RBI", authority_level: "primary_official" } }] }],
    generation_runs: [], warnings: [],
  };
}

beforeEach(() => {
  collectionArgs = undefined;
  lastAction = undefined;
  mockCollection = {
    items: [{ id: CAND, status: "review_ready", validation_result: { ok: true },
              question_payload: { stem: "Which body issued the June 2026 circular?" } }],
    status: "ready", total: 1, refresh: jest.fn(),
  };
  mockApi.getCaCandidate.mockReset().mockResolvedValue(envelope("review_ready"));
  mockApi.reviewCaCandidate.mockClear();
  mockApi.promoteCaCandidate.mockClear();
});

const PERMS = { canReview: true, canPublish: false };

test("subscribes the collection to the real (url, seed, {params}) contract", () => {
  render(<CaQuestionReviewQueue perms={PERMS} />);
  expect(collectionArgs.url).toBe("/api/admin/content-studio/ca-question-candidates");
  expect(Array.isArray(collectionArgs.seed)).toBe(true);
  expect(collectionArgs.options.params).toEqual({ status: "review_ready", limit: 25, offset: 0 });
});

test("drill-in renders the evidence envelope (claim + source authority)", async () => {
  render(<CaQuestionReviewQueue perms={PERMS} />);
  fireEvent.click(screen.getByTestId(`ca-review-open-${CAND}`));
  await waitFor(() => expect(mockApi.getCaCandidate).toHaveBeenCalledWith(CAND));
  expect(await screen.findByTestId("ca-review-claim-c1")).toHaveTextContent("RBI issued a circular");
  expect(screen.getByTestId("ca-review-source-authority")).toHaveTextContent("primary_official");
});

test("approve sends dual-CAS status + updated_at token + audit reason", async () => {
  render(<CaQuestionReviewQueue perms={PERMS} />);
  fireEvent.click(screen.getByTestId(`ca-review-open-${CAND}`));
  await screen.findByTestId("ca-review-decision");
  fireEvent.change(screen.getByTestId("ca-review-reason"), { target: { value: "looks accurate and current" } });
  fireEvent.change(screen.getByTestId("ca-review-decision"), { target: { value: "approved" } });
  fireEvent.click(screen.getByTestId("ca-review-submit"));
  await waitFor(() =>
    expect(mockApi.reviewCaCandidate).toHaveBeenCalledWith(CAND, {
      status: "approved", expected_status: "review_ready", expected_updated_at: TOKEN,
      reason: "looks accurate and current", reviewer_notes: undefined,
    })
  );
});

test("submit disabled until a valid reason is entered", async () => {
  render(<CaQuestionReviewQueue perms={PERMS} />);
  fireEvent.click(screen.getByTestId(`ca-review-open-${CAND}`));
  await screen.findByTestId("ca-review-decision");
  fireEvent.change(screen.getByTestId("ca-review-decision"), { target: { value: "approved" } });
  expect(screen.getByTestId("ca-review-submit")).toBeDisabled(); // no reason yet
  fireEvent.change(screen.getByTestId("ca-review-reason"), { target: { value: "valid reason text" } });
  expect(screen.getByTestId("ca-review-submit")).not.toBeDisabled();
});

test("promote hidden without publish permission", async () => {
  mockApi.getCaCandidate.mockResolvedValue(envelope("approved"));
  render(<CaQuestionReviewQueue perms={{ canReview: true, canPublish: false }} />);
  fireEvent.click(screen.getByTestId(`ca-review-open-${CAND}`));
  await screen.findByTestId("ca-review-dialog");
  expect(screen.queryByTestId("ca-review-promote")).not.toBeInTheDocument();
});

test("promote sends CAS token + reason when publish-permitted", async () => {
  mockApi.getCaCandidate.mockResolvedValue(envelope("approved"));
  render(<CaQuestionReviewQueue perms={{ canReview: true, canPublish: true }} />);
  fireEvent.click(screen.getByTestId(`ca-review-open-${CAND}`));
  await screen.findByTestId("ca-review-promote");
  fireEvent.change(screen.getByTestId("ca-review-reason"), { target: { value: "evidence checks out" } });
  fireEvent.click(screen.getByTestId("ca-review-promote"));
  await waitFor(() =>
    expect(mockApi.promoteCaCandidate).toHaveBeenCalledWith(CAND, {
      expected_status: "approved", expected_updated_at: TOKEN, reason: "evidence checks out",
    })
  );
});
