import React, { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import AuthLayout from "./AuthLayout";
import { useAuth } from "../../lib/authContext";
import { resolvePostAuthRedirect } from "../../lib/resolvePostAuthRedirect";
import { useTurnstileChallenge } from "../../lib/useTurnstileChallenge";
import { stashMergeClaim } from "../../features/onboarding-chat/mergeClaim";
import { normalizePhoneE164 } from "../../lib/phone";

function humanizeAuthError(err) {
  const raw = (err && (err.message || err.error_description)) || "Unable to sign in";
  if (/captcha|turnstile/i.test(raw)) {
    return "Verification failed. Please try again.";
  }
  return raw;
}

// With shouldCreateUser:false, Supabase rejects an unknown phone rather than
// minting an account. Detect that family of messages so we can route the user
// to signup instead of surfacing a confusing "signups not allowed" error.
function isUnknownUserError(err) {
  const raw = (err && (err.message || err.error_description)) || "";
  return /signups?\s+not\s+allowed|user\s+not\s+found|otp_disabled|not\s+exist/i.test(raw);
}

export default function Login() {
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState("phone"); // phone | code
  const [sentTo, setSentTo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const auth = useAuth();
  const nav = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const redirectTo = resolvePostAuthRedirect(location, searchParams, "/app");
  const {
    Turnstile,
    captchaRequired,
    widgetFailed,
    waitForCaptchaToken,
    reset: resetCaptcha,
  } = useTurnstileChallenge();

  const urlError = useMemo(() => searchParams.get("error"), [searchParams]);
  const [bannerError, setBannerError] = useState(urlError);

  useEffect(() => {
    stashMergeClaim(searchParams.get("merge_claim"));
  }, [searchParams]);

  async function handleGoogleSignIn() {
    setLoading(true);
    setError(null);
    setBannerError(null);
    try {
      await auth.loginWithGoogle({ redirectTo });
    } catch (err) {
      setError(err.message || "Unable to sign in with Google");
      setLoading(false);
    }
  }

  async function getCaptcha() {
    if (!captchaRequired) return undefined;
    try {
      return await waitForCaptchaToken({ timeoutMs: 15000 });
    } catch (capErr) {
      if (widgetFailed || capErr?.message === "captcha_widget_failed") {
        throw new Error("CAPTCHA failed to load. Disable ad-blockers or try another browser.");
      }
      return undefined; // widget alive — let Supabase reject cleanly
    }
  }

  async function handleSendCode(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setBannerError(null);
    const e164 = normalizePhoneE164(phone);
    if (!e164) {
      setError("Enter a valid phone number with country code.");
      setLoading(false);
      return;
    }
    try {
      const captchaToken = await getCaptcha();
      // Login NEVER creates a new account. An unknown phone is rejected by
      // Supabase (shouldCreateUser:false) and routed to /signup below.
      await auth.requestPhoneOtp(e164, { captchaToken, shouldCreateUser: false });
      setSentTo(e164);
      setStep("code");
    } catch (err) {
      if (isUnknownUserError(err)) {
        nav(`/signup?phone=${encodeURIComponent(e164)}`, { replace: false });
        return;
      }
      setError(humanizeAuthError(err));
    } finally {
      // Turnstile tokens are single-use — reset after EVERY send (success or
      // failure) so a Resend / number edit always mints a fresh token.
      resetCaptcha();
      setLoading(false);
    }
  }

  async function handleVerify(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const user = await auth.verifyPhoneOtp(sentTo, code.trim());
      if (user.role === "admin" || user.role === "super_admin") {
        nav("/admin", { replace: true });
      } else {
        nav(redirectTo, { replace: true });
      }
    } catch (err) {
      setError(humanizeAuthError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setLoading(true);
    setError(null);
    try {
      const captchaToken = await getCaptcha();
      // sentTo already passed shouldCreateUser:false on the first send; the
      // account exists by now, so a plain resend is correct here.
      await auth.requestPhoneOtp(sentTo, { captchaToken, shouldCreateUser: false });
    } catch (err) {
      setError(humanizeAuthError(err));
    } finally {
      resetCaptcha();
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Welcome back."
      subtitle="Sign in to continue your 90-day plan."
      footer={
        <span>
          New here?{" "}
          <Link to="/signup" className="link-under font-semibold">
            Create your account
          </Link>
        </span>
      }
    >
      <div className="space-y-5" data-testid="login-form">
        {bannerError && (
          <div
            className="rounded-xl bg-destructive/10 border border-destructive/30 text-destructive text-sm px-3 py-2"
            data-testid="login-banner-error"
          >
            {bannerError}
          </div>
        )}
        <button
          type="button"
          onClick={handleGoogleSignIn}
          disabled={loading}
          data-testid="login-google"
          className="btn btn-ghost w-full disabled:opacity-60"
        >
          Continue with Google
        </button>
        <div className="text-[11px] uppercase tracking-widest text-muted-foreground text-center">
          or sign in with your phone
        </div>

        {step === "phone" ? (
          <form onSubmit={handleSendCode} className="space-y-5">
            <div>
              <label className="block text-[11px] uppercase tracking-widest text-muted-foreground mb-1.5">
                Phone number
              </label>
              <input
                data-testid="login-phone"
                type="tel"
                required
                autoComplete="tel"
                placeholder="+91 98765 43210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-white/80 border border-border focus:border-clay-400 outline-none text-sm"
              />
              <p className="mt-1 text-[11px] text-muted-foreground">
                Include your country code (e.g. +91 for India).
              </p>
            </div>
            {error && (
              <div className="rounded-xl bg-destructive/10 border border-destructive/30 text-destructive text-sm px-3 py-2" data-testid="login-error">
                {error}
              </div>
            )}
            <Turnstile />
            <button
              type="submit"
              disabled={loading}
              data-testid="login-send-code"
              className="btn btn-primary w-full disabled:opacity-60"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />} Send code
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerify} className="space-y-5">
            <div>
              <label className="block text-[11px] uppercase tracking-widest text-muted-foreground mb-1.5">
                Enter the 6-digit code
              </label>
              <input
                data-testid="login-otp"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]*"
                maxLength={6}
                required
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                className="w-full px-4 py-3 rounded-xl bg-white/80 border border-border focus:border-clay-400 outline-none text-sm tracking-[0.4em] text-center"
              />
              <p className="mt-1 text-[11px] text-muted-foreground" data-testid="login-otp-sentto">
                Sent to {sentTo}.{" "}
                <button type="button" onClick={() => { setStep("phone"); setCode(""); }} className="link-under">
                  Change number
                </button>
              </p>
            </div>
            {error && (
              <div className="rounded-xl bg-destructive/10 border border-destructive/30 text-destructive text-sm px-3 py-2" data-testid="login-error">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={loading}
              data-testid="login-verify"
              className="btn btn-primary w-full disabled:opacity-60"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />} Verify & sign in
            </button>
            <button
              type="button"
              onClick={handleResend}
              disabled={loading}
              data-testid="login-resend"
              className="btn btn-ghost w-full text-xs disabled:opacity-60"
            >
              Resend code
            </button>
          </form>
        )}

        <div className="text-[11px] text-muted-foreground text-center">
          Auth powered by Supabase. New here?{" "}
          <Link to="/signup" className="link-under">Create an account</Link>.
        </div>
      </div>
    </AuthLayout>
  );
}
