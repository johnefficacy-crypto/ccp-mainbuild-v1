import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, Loader2 } from "lucide-react";
import { useAuth } from "../../lib/authContext";
import { api } from "../../lib/api";

// Sticky-ish top banner shown only while the user is anonymous. Calls
// supabase.auth.linkIdentity({provider:'google'}) which keeps the
// same user_id and flips is_anonymous=false on success. If the email
// is already attached to a different account, linking is impossible —
// instead of abandoning the anon profile we mint a single-use merge
// claim (while we still hold the anon session), sign out, and carry the
// token to the login page so the permanent account can absorb the
// onboarding progress after Google sign-in.
export default function GoogleLinkBanner() {
  const { linkGoogleIdentity, logout, user } = useAuth();
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  if (!user?.is_anonymous) return null;

  const handleConflict = async () => {
    // Mint the merge claim BEFORE signing out — the create endpoint needs
    // the anon session. If it fails for any reason, degrade gracefully to
    // the old behaviour (plain logout + conflict notice) rather than
    // blocking the user from logging into their real account.
    let token = null;
    try {
      const resp = await api.post("/api/onboarding/merge-claim/create", {});
      token = resp?.token || null;
    } catch (e) {
      token = null;
    }
    await logout();
    if (token) {
      navigate(
        `/login?merge_claim=${encodeURIComponent(token)}&conflict=true`
      );
    } else {
      navigate("/login?conflict=true");
    }
  };

  const handleLink = async () => {
    setPending(true);
    setError(null);
    try {
      const result = await linkGoogleIdentity();
      if (result?.ok) {
        // Supabase will redirect — nothing else to do here.
        return;
      }
      if (result?.conflict) {
        await handleConflict();
        return;
      }
      setError(result?.error || "Couldn't link your Google account");
    } catch (e) {
      setError(e?.message || "Couldn't link your Google account");
    } finally {
      setPending(false);
    }
  };

  return (
    <div
      data-testid="google-link-banner"
      className="soft-card rounded-2xl p-3 flex items-center gap-2 border border-clay-200"
    >
      <Sparkles className="h-4 w-4 text-clay-500 shrink-0" aria-hidden="true" />
      <div className="flex-1 text-xs text-clay-800">
        Sign in with Google to save your progress permanently.
      </div>
      <button
        type="button"
        onClick={handleLink}
        disabled={pending}
        className="btn btn-primary text-xs"
        data-testid="google-link-button"
      >
        {pending ? <Loader2 className="h-3 w-3 animate-spin" /> : "Sign in with Google"}
      </button>
      {error && <p className="text-xs text-amber-700 ml-2">{error}</p>}
    </div>
  );
}
