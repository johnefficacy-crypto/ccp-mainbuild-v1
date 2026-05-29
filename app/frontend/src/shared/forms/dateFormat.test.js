import {
  formatDDMMYYYY,
  parseDDMMYYYY,
  isoToLocalDate,
  localDateToIso,
} from "./dateFormat";

test("formatDDMMYYYY renders ISO date-only as dd-mm-yyyy", () => {
  expect(formatDDMMYYYY("2026-03-12")).toBe("12-03-2026");
  expect(formatDDMMYYYY("2026-03-12T10:30:00Z")).toBe("12-03-2026");
  expect(formatDDMMYYYY(null)).toBe("");
  expect(formatDDMMYYYY("garbage")).toBe("");
});

test("parseDDMMYYYY converts dd-mm-yyyy to ISO", () => {
  expect(parseDDMMYYYY("12-03-2026")).toBe("2026-03-12");
  expect(parseDDMMYYYY(" 01-01-2000 ")).toBe("2000-01-01");
});

test("parseDDMMYYYY rejects invalid input", () => {
  expect(parseDDMMYYYY("32-13-2026")).toBe(null);
  expect(parseDDMMYYYY("31-02-2026")).toBe(null);
  expect(parseDDMMYYYY("2026-03-12")).toBe(null);
  expect(parseDDMMYYYY("")).toBe(null);
  expect(parseDDMMYYYY("1-1-2026")).toBe(null);
});

test("formatDDMMYYYY + parseDDMMYYYY roundtrip", () => {
  const iso = "2026-03-12";
  expect(parseDDMMYYYY(formatDDMMYYYY(iso))).toBe(iso);
  const text = "09-11-1999";
  expect(formatDDMMYYYY(parseDDMMYYYY(text))).toBe(text);
});

test("isoToLocalDate / localDateToIso roundtrip without timezone shift", () => {
  const iso = "2026-03-12";
  expect(localDateToIso(isoToLocalDate(iso))).toBe(iso);
  // The local Date carries the exact calendar day, not a UTC-shifted one.
  const d = isoToLocalDate(iso);
  expect(d.getFullYear()).toBe(2026);
  expect(d.getMonth()).toBe(2);
  expect(d.getDate()).toBe(12);
});
