import React, { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { supabase } from "../../lib/supabase";
import { api } from "../../lib/api";
import {
  peekAnonymousId,
  clearAnonymousId,
} from "../../features/onboarding-chat/anonymousId";
import {
  peekMergeClaim,
  clearMergeClaim,
} from "../../features/onboarding-chat/mergeClaim";
import { resolvePostAuthRedirect } from "../../lib/resolvePostAuthRedirect";
import { useToast } from "../../shared/ui/ToastProvider";

const STITCH_TIMEOUT_MS = 3000;

export default function AuthCallback() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const toast = useToast();

  useEffect(() => {
    let mounted = true;

    async function finish() {
      // 1. OAuth provider errors arrive as query params.
      const providerError =
        params.get("error_description") || params.get("error");
      if (providerError) {
        if (mounted) {
          nav(`/login?error=${encodeURIComponent(providerError)}`, {
            replace: true,
          });
        }
        return;
      }

      // 2. Read the session. The client was created with default
      //    detectSessionInUrl=true, which already exchanged the `?code=`
      //    on init. Calling exchangeCodeForSession again here would
      //    throw "both auth code and code verifier should be non-empty".
      let session;
      try {
        const { data, error } = await supabase.auth.getSession();
        if (error) {
          if (mounted) {
            nav(`/login?error=${encodeURIComponent(error.message)}`, {
              replace: true,
            });
          }
          return;
        }
        session = data?.session;
      } catch (e) {
        if (mounted) {
          nav(
            `/login?error=${encodeURIComponent(e?.message || "auth_callback_failed")}`,
            { replace: true }
          );
        }
        return;
      }

      if (!session) {
        if (mounted) {
          nav(`/login?error=auth_session_missing`, { replace: true });
        }
        return;
      }

      // 3. Stitch anonymous onboarding rows onto the new user, fire-and-forget.
      //    Backend is idempotent via stitch_anonymous_sessions, so a missed
      //    stitch can be retried on any later authed call — never block nav.
      const anonId = peekAnonymousId();
      if (anonId) {
        const stitchPromise = api.post(
          "/api/onboarding-unified/stitch-anonymous",
          { anonymous_id: anonId },
          {
            headers: { Authorization: `Bearer ${session.access_token}` },
          }
        );
        Promise.race([
          stitchPromise,
          new Promise((_, rej) =>
            setTimeout(() => rej(new Error("stitch_timeout")), STITCH_TIMEOUT_MS)
          ),
        ])
          .then(() => clearAnonymousId())
          .catch(() => {
            /* non-blocking; a later authed request can re-stitch */
          });
      }

      // 3b. Consume an anonymous→permanent merge claim, if one was carried
      //     through the conflict flow. Fire-and-forget: navigation below does
      //     not wait on it, and the toast fires whenever the request settles
      //     because ToastProvider lives above the router. The token is
      //     single-use and the merge RPC is idempotent, so we clear it on any
      //     settle to avoid a stale token lingering in sessionStorage.
      const mergeToken = peekMergeClaim();
      if (mergeToken) {
        api
          .post(
            "/api/onboarding/merge-claim/consume",
            { token: mergeToken },
            { headers: { Authorization: `Bearer ${session.access_token}` } }
          )
          .then(() => {
            clearMergeClaim();
            toast.success("We restored the progress from your earlier session.");
          })
          .catch(() => {
            clearMergeClaim();
            toast.error(
              "You're signed in, but we couldn't merge your earlier progress."
            );
          });
      }

      // 4. Resolve a safe redirect and navigate immediately.
      const target = resolvePostAuthRedirect({ next: params.get("next") });
      if (mounted) nav(target, { replace: true });
    }

    finish();
    return () => {
      mounted = false;
    };
  }, [nav, params, toast]);

  return (
    <div className="min-h-screen flex items-center justify-center linen-bg">
      <div className="text-sm text-muted-foreground" data-testid="auth-callback-progress">
        Completing sign in…
      </div>
    </div>
  );
}
