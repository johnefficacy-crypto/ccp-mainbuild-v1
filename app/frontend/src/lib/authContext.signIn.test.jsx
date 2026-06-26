import React from "react";
import { render, act, waitFor } from "@testing-library/react";

const mockGetSession = jest.fn();
const mockSignInAnonymously = jest.fn();
const mockSignInWithOtp = jest.fn();
const mockVerifyOtp = jest.fn();
const mockAuthMe = jest.fn();
// Capture the onAuthStateChange callback so tests can simulate Supabase firing
// SIGNED_IN (the source of the hydrate race).
let authStateCb = null;

jest.mock("./supabase", () => ({
  __esModule: true,
  supabase: {
    auth: {
      getSession: (...args) => mockGetSession(...args),
      signInAnonymously: (...args) => mockSignInAnonymously(...args),
      signInWithOtp: (...args) => mockSignInWithOtp(...args),
      verifyOtp: (...args) => mockVerifyOtp(...args),
      onAuthStateChange: (cb) => {
        authStateCb = cb;
        return { data: { subscription: { unsubscribe: jest.fn() } } };
      },
      signOut: jest.fn(),
      signInWithOAuth: jest.fn(),
      linkIdentity: jest.fn(),
    },
  },
}));

jest.mock("./api", () => ({
  __esModule: true,
  auth: { me: (...args) => mockAuthMe(...args) },
}));

beforeEach(() => {
  mockGetSession.mockReset();
  mockSignInAnonymously.mockReset();
  mockSignInWithOtp.mockReset();
  mockVerifyOtp.mockReset();
  mockAuthMe.mockReset();
  authStateCb = null;
  mockGetSession.mockResolvedValue({ data: { session: null } });
});

function Capture({ onReady }) {
  // eslint-disable-next-line global-require
  const { useAuth } = require("./authContext");
  const auth = useAuth();
  React.useEffect(() => {
    onReady(auth);
  }, [auth, onReady]);
  return null;
}

function mount() {
  // eslint-disable-next-line global-require
  const { AuthProvider } = require("./authContext");
  let captured;
  const onReady = (val) => {
    captured = val;
  };
  render(
    <AuthProvider>
      <Capture onReady={onReady} />
    </AuthProvider>,
  );
  return () => captured;
}

test("signInAnonymously surfaces Supabase error message, code, and status", async () => {
  mockSignInAnonymously.mockResolvedValue({
    data: { session: null },
    error: {
      message: "captcha protection: request disallowed (captcha_failed)",
      code: "captcha_failed",
      status: 400,
    },
  });

  const get = mount();
  await waitFor(() => expect(typeof get()?.signInAnonymously).toBe("function"));

  let thrown;
  await act(async () => {
    try {
      await get().signInAnonymously({ captchaToken: "tok" });
    } catch (e) {
      thrown = e;
    }
  });

  expect(thrown).toBeInstanceOf(Error);
  expect(thrown.message).toMatch(/captcha protection/);
  expect(thrown.message).toMatch(/code=captcha_failed/);
  expect(thrown.message).toMatch(/status=400/);
});

test("signInAnonymously passes the captcha token through to Supabase", async () => {
  mockSignInAnonymously.mockResolvedValue({
    data: {
      session: {
        access_token: "jwt-xyz",
        user: { id: "anon-1", is_anonymous: true, user_metadata: {}, app_metadata: {} },
      },
      user: { id: "anon-1", is_anonymous: true, user_metadata: {}, app_metadata: {} },
    },
    error: null,
  });
  mockAuthMe.mockRejectedValue(new Error("backend offline"));

  const get = mount();
  await waitFor(() => expect(typeof get()?.signInAnonymously).toBe("function"));

  await act(async () => {
    await get().signInAnonymously({ captchaToken: "abc-token" });
  });

  expect(mockSignInAnonymously).toHaveBeenCalledWith({
    options: { captchaToken: "abc-token" },
  });
});

test("requestPhoneOtp sends an SMS OTP with shouldCreateUser + captcha + data", async () => {
  mockSignInWithOtp.mockResolvedValue({ data: {}, error: null });
  const get = mount();
  await waitFor(() => expect(typeof get()?.requestPhoneOtp).toBe("function"));

  await act(async () => {
    await get().requestPhoneOtp("+919999900001", { captchaToken: "tok", data: { name: "Asha" } });
  });

  expect(mockSignInWithOtp).toHaveBeenCalledWith({
    phone: "+919999900001",
    options: { shouldCreateUser: true, data: { name: "Asha" }, captchaToken: "tok" },
  });
});

test("requestPhoneOtp forwards shouldCreateUser:false (login never creates accounts)", async () => {
  mockSignInWithOtp.mockResolvedValue({ data: {}, error: null });
  const get = mount();
  await waitFor(() => expect(typeof get()?.requestPhoneOtp).toBe("function"));

  await act(async () => {
    await get().requestPhoneOtp("+919999900001", { shouldCreateUser: false });
  });

  expect(mockSignInWithOtp).toHaveBeenCalledWith({
    phone: "+919999900001",
    options: { shouldCreateUser: false },
  });
});

test("hydrate race: SIGNED_IN during verifyOtp still yields the backend user, /me hit once", async () => {
  const session = {
    access_token: "jwt-race",
    user: { id: "u1", phone: "+919999900001", user_metadata: {}, app_metadata: {} },
  };
  mockVerifyOtp.mockResolvedValue({ data: { session, user: session.user }, error: null });
  // Slow backend so both callers (onAuthStateChange + verifyPhoneOtp) overlap.
  let resolveMe;
  mockAuthMe.mockReturnValue(
    new Promise((res) => {
      resolveMe = () => res({ user: { id: "u1", role: "user", phone: "+919999900001" } });
    }),
  );

  const get = mount();
  await waitFor(() => expect(typeof get()?.verifyPhoneOtp).toBe("function"));

  let user;
  await act(async () => {
    // Simulate Supabase firing SIGNED_IN with the same session first…
    authStateCb("SIGNED_IN", session);
    // …then verifyPhoneOtp calls hydrate() with the same token (the race).
    const p = get().verifyPhoneOtp("+919999900001", "123456");
    resolveMe();
    user = await p;
  });

  // Both hydrate() calls share one in-flight promise → exactly one /me round-trip.
  expect(mockAuthMe).toHaveBeenCalledTimes(1);
  // The verifyPhoneOtp return MUST be the real backend user, never a stale null.
  expect(user).toBeTruthy();
  expect(user.role).toBe("user");
  expect(user.phone).toBe("+919999900001");
});

test("verifyPhoneOtp verifies the sms code and hydrates", async () => {
  mockVerifyOtp.mockResolvedValue({
    data: {
      session: { access_token: "jwt-1", user: { id: "u1", phone: "+919999900001", user_metadata: {}, app_metadata: {} } },
      user: { id: "u1", phone: "+919999900001", user_metadata: {}, app_metadata: {} },
    },
    error: null,
  });
  mockAuthMe.mockResolvedValue({ user: { id: "u1", role: "user", phone: "+919999900001" } });

  const get = mount();
  await waitFor(() => expect(typeof get()?.verifyPhoneOtp).toBe("function"));

  let user;
  await act(async () => {
    user = await get().verifyPhoneOtp("+919999900001", "123456");
  });

  expect(mockVerifyOtp).toHaveBeenCalledWith({ phone: "+919999900001", token: "123456", type: "sms" });
  expect(user.phone).toBe("+919999900001");
});

test("password login/register methods are removed", async () => {
  const get = mount();
  await waitFor(() => expect(typeof get()?.requestPhoneOtp).toBe("function"));
  expect(get().login).toBeUndefined();
  expect(get().register).toBeUndefined();
  expect(get().sendPasswordReset).toBeUndefined();
  expect(get().updatePassword).toBeUndefined();
});
