import React, { useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import AuthLayout from "./AuthLayout";
import { useAuth } from "../../lib/authContext";
import { resolvePostAuthRedirect } from "../../lib/resolvePostAuthRedirect";
import { useTurnstileChallenge } from "../../lib/useTurnstileChallenge";
import { normalizePhoneE164 } from "../../lib/phone";

const SIGNUP_DEFAULT = "/app/onboarding/chat?mode=discovery";

function humanizeAuthError(err) {
  const raw = (err && (err.message || err.error_description)) || "Unable to create account";
  if (/captcha|turnstile/i.test(raw)) {
    return "Verification failed. Please try again.";
  }
  return raw;
}

export default function Signup() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState(""); // optional
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState("details"); // details | code
  const [sentTo, setSentTo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const auth = useAuth();
  const nav = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const redirectTo = resolvePostAuthRedirect(location, searchParams, SIGNUP_DEFAULT);
  const {
    Turnstile,
    captchaRequired,
    widgetFailed,
    waitForCaptchaToken,
    reset: resetCaptcha,
  } = useTurnstileChallenge();

  const urlError = useMemo(() => searchParams.get("error"), [searchParams]);
  const [bannerError, setBannerError] = useState(urlError);

  async function handleGoogleSignup() {
    setLoading(true);
    setError(null);
    setBannerError(null);
    try {
      await auth.loginWithGoogle({ redirectTo });
    } catch (err) {
      setError(err.message || "Unable to continue with Google");
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
      return undefined;
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
      await auth.requestPhoneOtp(e164, {
        captchaToken,
        data: { name: name.trim(), ...(email.trim() ? { email: email.trim() } : {}) },
      });
      setSentTo(e164);
      setStep("code");
    } catch (err) {
      resetCaptcha();
      setError(humanizeAuthError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await auth.verifyPhoneOtp(sentTo, code.trim());
      nav(redirectTo, { replace: true });
    } catch (err) {
      setError(humanizeAuthError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account."
      subtitle="Your 90-day plan begins with a 3-minute profile."
      footer={
        <span>
          Already joined?{" "}
          <Link to="/login" className="link-under font-semibold">Sign in</Link>
        </span>
      }
    >
      <div className="space-y-5" data-testid="signup-form">
        {bannerError && (
          <div
            className="rounded-xl bg-destructive/10 border border-destructive/30 text-destructive text-sm px-3 py-2"
            data-testid="signup-banner-error"
          >
            {bannerError}
          </div>
        )}
        <button
          type="button"
          onClick={handleGoogleSignup}
          disabled={loading}
          data-testid="signup-google"
          className="btn btn-ghost w-full disabled:opacity-60"
        >
          Continue with Google
        </button>
        <div className="text-[11px] uppercase tracking-widest text-muted-foreground text-center">
          or sign up with your phone
        </div>

        {step === "details" ? (
          <form onSubmit={handleSendCode} className="space-y-5">
            <div>
              <label className="block text-[11px] uppercase tracking-widest text-muted-foreground mb-1.5">Full name</label>
              <input
                data-testid="signup-name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-white/80 border border-border focus:border-clay-400 outline-none text-sm"
              />
            </div>
            <div>
              <label className="block text-[11px] uppercase tracking-widest text-muted-foreground mb-1.5">Phone number</label>
              <input
                data-testid="signup-phone"
                required
                type="tel"
                autoComplete="tel"
                placeholder="+91 98765 43210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-white/80 border border-border focus:border-clay-400 outline-none text-sm"
              />
              <p className="mt-1 text-[11px] text-muted-foreground">Include your country code (e.g. +91 for India).</p>
            </div>
            <div>
              <label className="block text-[11px] uppercase tracking-widest text-muted-foreground mb-1.5">
                Email <span className="normal-case tracking-normal text-muted-foreground/70">(optional)</span>
              </label>
              <input
                data-testid="signup-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-white/80 border border-border focus:border-clay-400 outline-none text-sm"
              />
              <div className="text-[11px] text-muted-foreground mt-1.5">For receipts and updates. You sign in with your phone.</div>
            </div>
            {error && (
              <div className="rounded-xl bg-destructive/10 border border-destructive/30 text-destructive text-sm px-3 py-2" data-testid="signup-error">
                {error}
              </div>
            )}
            <Turnstile />
            <button
              type="submit"
              disabled={loading}
              data-testid="signup-send-code"
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
                data-testid="signup-otp"
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
              <p className="mt-1 text-[11px] text-muted-foreground" data-testid="signup-otp-sentto">
                Sent to {sentTo}.{" "}
                <button type="button" onClick={() => { setStep("details"); setCode(""); }} className="link-under">
                  Edit details
                </button>
              </p>
            </div>
            {error && (
              <div className="rounded-xl bg-destructive/10 border border-destructive/30 text-destructive text-sm px-3 py-2" data-testid="signup-error">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={loading}
              data-testid="signup-verify"
              className="btn btn-primary w-full disabled:opacity-60"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />} Verify & create account
            </button>
          </form>
        )}
        <p className="text-[11px] text-muted-foreground text-center">
          By continuing you agree to our quiet principles: no spam, no rumors, no sale of your data.
        </p>
      </div>
    </AuthLayout>
  );
}
