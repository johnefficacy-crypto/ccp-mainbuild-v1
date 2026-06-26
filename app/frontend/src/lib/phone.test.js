import { normalizePhoneE164 } from "./phone";

test("keeps a valid + E.164 number", () => {
  expect(normalizePhoneE164("+919999900001")).toBe("+919999900001");
});

test("strips spaces, dashes, parens", () => {
  expect(normalizePhoneE164("+91 99999-00001")).toBe("+919999900001");
  expect(normalizePhoneE164("+1 (555) 555-0100")).toBe("+15555550100");
});

test("assumes +91 for a bare 10-digit number", () => {
  expect(normalizePhoneE164("9999900001")).toBe("+919999900001");
});

test("00 prefix becomes +", () => {
  expect(normalizePhoneE164("00919999900001")).toBe("+919999900001");
});

test("rejects too-short / non-numeric", () => {
  expect(normalizePhoneE164("123")).toBeNull();
  expect(normalizePhoneE164("")).toBeNull();
  expect(normalizePhoneE164(null)).toBeNull();
  expect(normalizePhoneE164("abcdef")).toBeNull();
});
