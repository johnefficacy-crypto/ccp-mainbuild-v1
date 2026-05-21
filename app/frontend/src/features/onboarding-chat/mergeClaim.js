// Shared sessionStorage shuttle for the anonymous→permanent merge token.
//
// The token is minted by the anon session (GoogleLinkBanner), then has to
// survive a logout + the Google OAuth redirect round-trip before the permanent
// session can consume it. The Login page reads it off the URL and stashes it
// here; AuthCallback drains it after the permanent session is established.
// sessionStorage (not localStorage) so it dies with the tab and never leaks
// across sessions.

const MERGE_CLAIM_KEY = "ccp.merge_claim";

export function stashMergeClaim(token) {
  if (!token) return;
  try {
    window.sessionStorage.setItem(MERGE_CLAIM_KEY, token);
  } catch {
    /* storage disabled — degrade silently */
  }
}

export function peekMergeClaim() {
  try {
    return window.sessionStorage.getItem(MERGE_CLAIM_KEY) || null;
  } catch {
    return null;
  }
}

export function clearMergeClaim() {
  try {
    window.sessionStorage.removeItem(MERGE_CLAIM_KEY);
  } catch {
    /* no-op */
  }
}
