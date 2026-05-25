import React from "react";
import { render, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn(() => Promise.resolve({ items: [], total: 0 })) },
}));

// eslint-disable-next-line global-require
const { api } = require("../../../lib/api");
// eslint-disable-next-line global-require
const CmsRefField = require("./CmsRefField").default;

const CYCLE_FIELD = {
  key: "exam_cycle_id",
  type: "ref",
  ref: {
    endpoint: "exam-cycles",
    labelKey: "cycle_name",
    secondaryKey: "year",
    filters: { exam_id: "exam_id" },
  },
};

function Harness({ examId }) {
  return (
    <CmsRefField
      field={CYCLE_FIELD}
      value=""
      formValues={{ exam_id: examId }}
      onChange={() => {}}
      testId="cb"
    />
  );
}

test("child list refetches with the parent exam_id when the parent changes", async () => {
  api.get.mockResolvedValue({ items: [], total: 0 });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrap = (ui) => <QueryClientProvider client={client}>{ui}</QueryClientProvider>;

  const { rerender } = render(wrap(<Harness examId="exam-1" />));
  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("exam_id=exam-1")),
  );

  // Change the parent selection — the child query key changes, so the
  // cycle list is refetched scoped to the new exam.
  rerender(wrap(<Harness examId="exam-2" />));
  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("exam_id=exam-2")),
  );

  // And it hit the cycles endpoint, not some other table.
  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/exam-cycles?"));
});
