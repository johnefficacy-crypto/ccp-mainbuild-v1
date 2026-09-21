jest.mock("../shared/config/env", () => ({
  BACKEND_URL: "http://localhost:8000",
  API_TIMEOUT_MS: 5000,
}));

jest.mock("./supabase", () => ({
  supabase: { auth: { getSession: async () => ({ data: { session: null } }) } },
}));

import { apiFetch, getApiErrorDetail, getApiErrorMessage } from "./api";

describe("apiFetch error shape", () => {
  test("throws Error instance with enriched fields", async () => {
    global.fetch = jest.fn(async () => ({
      ok: false,
      status: 409,
      headers: { get: () => "application/json" },
      json: async () => ({ detail: { code: "X", blocking_issues: ["a"] } }),
      text: async () => "",
    }));
    await expect(apiFetch("/api/test")).rejects.toBeInstanceOf(Error);
    try {
      await apiFetch("/api/test");
    } catch (err) {
      expect(err.status).toBe(409);
      expect(err.code).toBe("X");
      expect(err.blocking_issues).toEqual(["a"]);
    }
  });
});

describe("coded 409 detail — {detail, code} (PRACTICE-PAPER-01)", () => {
  // practice/start answers an empty pool with {"detail": "<human text>",
  // "code": "<machine code>"}. FastAPI nests that one level, so without a
  // dedicated branch the formatter falls through to String(detail) and the
  // learner sees "[object Object]".
  test("renders the human text, not the object", () => {
    const err = new Error("conflict");
    err.status = 409;
    err.detail = {
      detail: "Descriptive paper — answer-writing practice not available yet.",
      code: "descriptive_paper",
    };
    expect(getApiErrorMessage(err)).toBe(
      "Descriptive paper — answer-writing practice not available yet."
    );
    expect(getApiErrorMessage(err)).not.toMatch(/object Object/);
  });

  test("a plain string detail still works", () => {
    const err = new Error("conflict");
    err.detail = "No verified, projected PYQ questions match this practice selection.";
    expect(getApiErrorMessage(err)).toBe(
      "No verified, projected PYQ questions match this practice selection."
    );
  });

  test("the machine code stays available alongside the text", () => {
    const err = new Error("conflict");
    err.detail = { detail: "human", code: "thematic_not_paper" };
    expect(getApiErrorDetail(err).code).toBe("thematic_not_paper");
  });
});
