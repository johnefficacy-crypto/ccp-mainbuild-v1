// Normalize a user-typed phone number to E.164 (the format Supabase phone OTP
// requires). Strips spaces/dashes/parens. A leading "+" is kept; a bare
// 10-digit number is assumed Indian (+91) since this is an India-first exam app.
// Returns null when the result is not a plausible E.164 number.
export function normalizePhoneE164(raw, defaultCountryCode = "91") {
  if (!raw) return null;
  let s = String(raw).trim().replace(/[\s\-().]/g, "");
  if (s.startsWith("00")) s = `+${s.slice(2)}`;
  if (!s.startsWith("+")) {
    const digits = s.replace(/\D/g, "");
    if (digits.length === 10) {
      s = `+${defaultCountryCode}${digits}`;
    } else if (digits.length > 10) {
      s = `+${digits}`; // already carries a country code, just missing the +
    } else {
      return null;
    }
  }
  // E.164: "+" followed by 8–15 digits.
  return /^\+[1-9]\d{7,14}$/.test(s) ? s : null;
}
