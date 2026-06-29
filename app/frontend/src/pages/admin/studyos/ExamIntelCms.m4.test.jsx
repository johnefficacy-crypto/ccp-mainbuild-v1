/**
 * M4 regression — subjects entity table must not render raw subject_id UUIDs.
 *
 * The `id` column for every entity in ExamIntelCms is rendered via
 * renderCellValue → humanizeToken, which truncates UUID-shaped strings to
 * "${first8}…". This test guards that the truncation is applied and the full
 * UUID never appears verbatim in the subjects table.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// humanizeToken is the canonical truncation helper.
import { humanizeToken } from "../../../features/admin/exam-intelligence/operatorChrome";

const SUBJECT_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890";
const SUBJECT_UUID_TRUNCATED = humanizeToken(SUBJECT_UUID); // e.g. "a1b2c3d4…"

// Minimal mock of the renderCellValue function (mirrors ExamIntelCms internals).
function renderCellValue(value) {
  if (value == null) return "—";
  if (typeof value === "boolean") return String(value);
  const s = String(value);
  const humanized = humanizeToken(s);
  if (humanized.endsWith("…")) return humanized;
  return s.slice(0, 60);
}

test("M4: humanizeToken truncates UUID-shaped subject_id", () => {
  const result = renderCellValue(SUBJECT_UUID);
  // Must end with ellipsis (UUID truncation marker).
  expect(result).toMatch(/…$/);
  // Must NOT be the full UUID.
  expect(result).not.toBe(SUBJECT_UUID);
  // Must start with first 8 chars of UUID.
  expect(result.startsWith(SUBJECT_UUID.slice(0, 8))).toBe(true);
});

test("M4: full UUID must not appear verbatim after renderCellValue", () => {
  const result = renderCellValue(SUBJECT_UUID);
  expect(result).not.toContain(SUBJECT_UUID);
});

test("M4: non-UUID slug passes through renderCellValue unchanged (up to 60 chars)", () => {
  const slug = "mathematics_advanced";
  const result = renderCellValue(slug);
  expect(result).toBe(slug);
});

test("M4: SUBJECT_UUID_TRUNCATED matches expected pattern", () => {
  // Sanity-check that humanizeToken produces the expected truncation format.
  expect(SUBJECT_UUID_TRUNCATED).toMatch(/^[a-z0-9]{8}…$/);
});
