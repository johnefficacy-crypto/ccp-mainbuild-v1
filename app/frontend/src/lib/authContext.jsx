import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { auth as authApi } from "./api";
import { ADMIN_ROLES, ROLES } from "./rbac";
import { supabase } from "./supabase";

const AuthCtx = createContext(null);

function coerceRole(rawRole) {
  return Object.values(ROLES).includes(rawRole) ? rawRole : ROLES.USER;
}

function safeGoalExams(value) {
  return Array.isArray(value) ? value : [];
}

function mergeUser(supabaseUser, backendUser) {
  if (!supabaseUser && !backendUser) return null;
  const meta = supabaseUser?.user_metadata || {};
  const appMeta = supabaseUser?.app_metadata || {};
  // Role is backend-authoritative. NEVER trust user_metadata.role (client-
  // writable). app_metadata.role is admin-set and only used as a fallback when
  // the backend user is unavailable; role-based redirects must use the
  // backend-hydrated user (see verifyPhoneOtp / hydrate).
  const role = coerceRole(backendUser?.role || appMeta.role);
  // Supabase sets is_anonymous on the user object after signInAnonymously.
  // The backend also forwards it on /auth/me. Either side is authoritative.
  const isAnonymous = Boolean(
    backendUser?.is_anonymous ?? supabaseUser?.is_anonymous ?? appMeta.is_anonymous
  );
  // Mentor is a capability, never a role. Source it from the backend's
  // capabilities block (profiles.is_mentor); default to no capabilities.
  const capabilities = {
    mentor: Boolean(backendUser?.capabilities?.mentor),
  };
  return {
    id: supabaseUser?.id || backendUser?.id || null,
    email: supabaseUser?.email || backendUser?.email || null,
    phone: backendUser?.phone || supabaseUser?.phone || meta.phone || null,
    name: backendUser?.name || meta.name || meta.full_name || null,
    role,
    permissions: Array.isArray(backendUser?.permissions) ? backendUser.permissions : [],
    capabilities,
    avatar: backendUser?.avatar || meta.avatar_url || null,
    onboarded: backendUser?.onboarded ?? Boolean(meta.onboarded),
    plan: backendUser?.plan || meta.plan || "free",
    goal_exams: safeGoalExams(backendUser?.goal_exams || meta.goal_exams),
    is_anonymous: isAnonymous,
    created_at: backendUser?.created_at || supabaseUser?.created_at || null,
  };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState("checking"); // checking | guest | session_authed | backend_authed
  // Dedup concurrent hydrate() calls (e.g. onAuthStateChange + verifyPhoneOtp).
  // Three refs collaborate:
  //   lastHydratedTokenRef  — token of the last *completed* successful hydration
  //   lastHydratedUserRef   — result of that hydration (avoids stale closure)
  //   hydrateInFlightRef    — in-progress {token, promise} so a second caller
  //                           with the same token piggybacks instead of racing
  const lastHydratedTokenRef = useRef(null);
  const lastHydratedUserRef = useRef(null);
  const hydrateInFlightRef = useRef(null);

  // Returns the backend-authoritative merged user on success, or null when the
  // session is absent / the backend rejects the token. Callers that gate on
  // role (e.g. admin redirect) MUST use this return value, never a client-only
  // mergeUser(session.user, null).
  const hydrate = useCallback(async (session) => {
    if (!session?.user) {
      lastHydratedTokenRef.current = null;
      lastHydratedUserRef.current = null;
      hydrateInFlightRef.current = null;
      setUser(null);
      setStatus("guest");
      return null;
    }
    const token = session.access_token;

    // Concurrent-call dedup: if a hydration is already in flight for this
    // token (e.g. onAuthStateChange fired before verifyPhoneOtp called us),
    // piggyback on that promise instead of issuing a second backend call.
    // This is the fix for the SIGNED_IN race: returning a shared promise means
    // both callers get the real backend-hydrated user, not a stale null.
    if (hydrateInFlightRef.current?.token === token) {
      return hydrateInFlightRef.current.promise;
    }

    // Cache hit: already completed a successful hydration for this token.
    // Return the stored result (not a stale closure variable).
    if (lastHydratedTokenRef.current === token) {
      return lastHydratedUserRef.current;
    }

    const promise = (async () => {
      try {
        const { user: backendUser } = await authApi.me();
        const merged = mergeUser(session.user, backendUser);
        lastHydratedTokenRef.current = token;
        lastHydratedUserRef.current = merged;
        hydrateInFlightRef.current = null;
        setUser(merged);
        setStatus("backend_authed");
        return merged;
      } catch (err) {
        hydrateInFlightRef.current = null;
        if (err?.status === 401) {
          // Token rejected by the backend — treat as a real auth loss and
          // clear state so the user gets a clean login prompt.
          lastHydratedTokenRef.current = null;
          lastHydratedUserRef.current = null;
          setUser(null);
          setStatus("guest");
        } else {
          // Network error or 5xx — backend is temporarily unreachable.
          // Reset the dedup refs so the next session event retries.
          lastHydratedTokenRef.current = null;
          lastHydratedUserRef.current = null;
        }
        return null;
      }
    })();

    hydrateInFlightRef.current = { token, promise };
    return promise;
  }, []);

  useEffect(() => {
    let mounted = true;
    supabase.auth
      .getSession()
      .then(({ data }) => {
        if (mounted) hydrate(data.session);
      })
      .catch(() => {
        if (mounted) {
          setUser(null);
          setStatus("guest");
        }
      });

    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT") {
        lastHydratedTokenRef.current = null;
        lastHydratedUserRef.current = null;
        hydrateInFlightRef.current = null;
      }
      hydrate(session);
    });
    return () => {
      mounted = false;
      sub.subscription.unsubscribe();
    };
  }, [hydrate]);

  // Phone/SMS OTP — step 1: send a one-time code to the phone (E.164).
  // `data` carries optional signup metadata ({ name, email }) → user_metadata.
  // shouldCreateUser controls whether an unknown phone silently creates an
  // account: Signup passes true, Login passes false so an unknown number is
  // rejected (the caller routes the user to /signup) instead of minting a
  // brand-new account on a typo'd login.
  const requestPhoneOtp = useCallback(
    async (phone, { captchaToken, data, shouldCreateUser = true } = {}) => {
      const { error } = await supabase.auth.signInWithOtp({
        phone,
        options: {
          shouldCreateUser,
          ...(data ? { data } : {}),
          ...(captchaToken ? { captchaToken } : {}),
        },
      });
      if (error) throw new Error(error.message || "Unable to send code");
      return { ok: true };
    },
    []
  );

  // Phone/SMS OTP — step 2: verify the code, establishing the session.
  const verifyPhoneOtp = useCallback(
    async (phone, token) => {
      const { data, error } = await supabase.auth.verifyOtp({
        phone,
        token,
        type: "sms",
      });
      if (error) throw new Error(error.message || "Invalid or expired code");
      // Return the BACKEND-hydrated user so role-based redirects use the
      // authoritative role, not client-writable session metadata. If the
      // backend is unreachable, hydrate() returns null → caller treats the
      // user as non-privileged (no admin redirect).
      const merged = await hydrate(data.session);
      return merged ?? { role: ROLES.USER };
    },
    [hydrate]
  );


  const loginWithGoogle = useCallback(async ({ redirectTo } = {}) => {
    // Only path-relative internal destinations are accepted; full URLs or
    // protocol-relative values fall back to /app so we can never bounce the
    // user to an attacker-controlled origin after OAuth.
    const next =
      typeof redirectTo === "string" &&
      redirectTo.startsWith("/") &&
      !redirectTo.startsWith("//") &&
      !redirectTo.startsWith("/\\")
        ? redirectTo
        : "/app";
    const callbackUrl = `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: callbackUrl },
    });
    if (error) throw new Error(error.message || "Unable to sign in with Google");
    return { ok: true };
  }, []);

  // Sign in as an anonymous Supabase user. Same user_id will survive
  // a later linkIdentity call, so any rows we wrote against this id
  // (profiles.persona_seed, etc.) follow the user into their permanent
  // account automatically. No-op when a session already exists.
  const signInAnonymously = useCallback(async ({ captchaToken } = {}) => {
    const { data: existing } = await supabase.auth.getSession();
    if (existing?.session?.access_token) {
      return { ok: true, existing: true };
    }
    const options = captchaToken ? { captchaToken } : undefined;
    const { data, error } = await supabase.auth.signInAnonymously(
      options ? { options } : undefined
    );
    if (error) {
      // Surface Supabase's status/code so the UI can distinguish a captcha
      // misconfiguration (400 with captcha_failed) from rate-limit / network
      // errors. The captcha-specific copy is added by the UI layer when it
      // sees this marker text.
      const parts = [
        error.message || "Unable to start anonymous session",
        error.code && `code=${error.code}`,
        error.status && `status=${error.status}`,
      ].filter(Boolean);
      throw new Error(parts.join(" "));
    }
    let session = data?.session;
    if (!session?.access_token) {
      // Supabase-js sometimes resolves before the session is persisted to
      // storage; re-read so callers can rely on an Authorization header
      // being available immediately after this resolves.
      const { data: reread } = await supabase.auth.getSession();
      session = reread?.session;
    }
    if (!session?.access_token) {
      throw new Error("Anonymous session was not created");
    }
    await hydrate(session);
    return { ok: true, existing: false };
  }, [hydrate]);

  // Promote the anonymous session into a Google-linked one. Supabase
  // updates `is_anonymous=false` on success. If the email is already
  // attached to another account we bubble that up so the caller can
  // route the user to a normal login flow instead.
  const linkGoogleIdentity = useCallback(async ({ redirectTo } = {}) => {
    const resolvedRedirect = redirectTo || `${window.location.origin}/app`;
    const { data, error } = await supabase.auth.linkIdentity({
      provider: "google",
      options: { redirectTo: resolvedRedirect },
    });
    if (error) {
      const message = error.message || "Unable to link Google";
      const conflict =
        /already|exists|linked/i.test(message) ||
        error.status === 409 ||
        error.code === "identity_already_exists";
      return { ok: false, conflict, error: message };
    }
    return { ok: true, data };
  }, []);
  const logout = useCallback(async () => {
    await supabase.auth.signOut();
    setUser(null);
    setStatus("guest");
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const { user: backendUser } = await authApi.me();
      const { data } = await supabase.auth.getSession();
      const merged = mergeUser(data.session?.user, backendUser);
      setUser(merged);
      setStatus(data.session?.user ? "backend_authed" : "guest");
      return merged;
    } catch {
      return null;
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      status,
      isAuthed: status === "session_authed" || status === "backend_authed",
      hasBackendSession: status === "backend_authed",
      isChecking: status === "checking",
      isAdmin: ADMIN_ROLES.includes(user?.role),
      isSuperAdmin: user?.role === ROLES.SUPER_ADMIN,
      isMentor: Boolean(user?.capabilities?.mentor),
      requestPhoneOtp,
      verifyPhoneOtp,
      logout,
      loginWithGoogle,
      signInAnonymously,
      linkGoogleIdentity,
      refreshUser,
      setUser,
    }),
    [
      user,
      status,
      requestPhoneOtp,
      verifyPhoneOtp,
      logout,
      loginWithGoogle,
      signInAnonymously,
      linkGoogleIdentity,
      refreshUser,
    ]
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
