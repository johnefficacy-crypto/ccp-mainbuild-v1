import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

jest.mock("../../../lib/api", () => {
  const get = jest.fn();
  return { __esModule: true, api: { get } };
});

import { api } from "../../../lib/api";
import PromotionPreviewPanel from "./PromotionPreviewPanel";

afterEach(() => {
  api.get.mockReset();
});

test("renders nothing and does not fetch when open is false", () => {
  api.get.mockResolvedValue({ ok: true });
  const { container } = render(<PromotionPreviewPanel queueId="q1" open={false} refreshKey={0} />);
  expect(container.firstChild).toBeNull();
  expect(api.get).not.toHaveBeenCalled();
});

test("fetches the preview once on mount when open", async () => {
  api.get.mockResolvedValue({ ok: true, recruitment_preview: { publish_status_after: "draft" } });
  render(<PromotionPreviewPanel queueId="q1" open refreshKey={0} />);
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
  expect(api.get).toHaveBeenCalledWith("/api/admin/scrape/items/q1/promotion-preview");
});

test("refetches when refreshKey bumps", async () => {
  api.get.mockResolvedValue({ ok: true });
  const { rerender } = render(<PromotionPreviewPanel queueId="q1" open refreshKey={0} />);
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
  rerender(<PromotionPreviewPanel queueId="q1" open refreshKey={1} />);
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
});
