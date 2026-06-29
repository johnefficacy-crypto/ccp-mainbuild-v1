import React from "react";
import { render, screen, act, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const mockRequestPhoneOtp = jest.fn();
const mockVerifyPhoneOtp = jest.fn();
const mockLoginWithGoogle = jest.fn();
const mockNavigate = jest.fn();

jest.mock("../../lib/authContext", () => ({
  __esModule: true,
  useAuth: () => ({
    requestPhoneOtp: mockRequestPhoneOtp,
    verifyPhoneOtp: mockVerifyPhoneOtp,
    loginWithGoogle: mockLoginWithGoogle,
  }),
}));

jest.mock("react-router-dom", () => {
  const actual = jest.requireActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockExecute = jest.fn();
const mockReset = jest.fn();
const cbs = { onSuccess: null, onError: null, onExpire: null };
jest.mock("../../components/TurnstileWidget", () => {
  const ReactInner = require("react");
  return {
    __esModule: true,
    default: ReactInner.forwardRef((props, ref) => {
      cbs.onSuccess = props.onSuccess;
      cbs.onError = props.onError;
      cbs.onExpire = props.onExpire;
      ReactInner.useImperativeHandle(ref, () => ({
        execute: mockExecute,
        reset: mockReset,
        remove: jest.fn(),
      }));
      return null;
    }),
  };
});

const ORIGINAL_KEY = process.env.REACT_APP_TURNSTILE_SITE_KEY;

beforeEach(() => {
  mockRequestPhoneOtp.mockReset();
  mockVerifyPhoneOtp.mockReset();
  mockLoginWithGoogle.mockReset();
  mockNavigate.mockReset();
  mockExecute.mockReset();
  mockReset.mockReset();
  cbs.onSuccess = null;
  cbs.onError = null;
  cbs.onExpire = null;
  process.env.REACT_APP_TURNSTILE_SITE_KEY = "site-key";
});
afterEach(() => {
  if (ORIGINAL_KEY === undefined) {
    delete process.env.REACT_APP_TURNSTILE_SITE_KEY;
  } else {
    process.env.REACT_APP_TURNSTILE_SITE_KEY = ORIGINAL_KEY;
  }
});

// eslint-disable-next-line global-require
const Signup = require("./Signup").default;

function renderSignup(path = "/signup") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Signup />
    </MemoryRouter>,
  );
}

async function fillAndSend({ email = "a@x.com" } = {}) {
  fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Alice" } });
  fireEvent.change(screen.getByTestId("signup-phone"), { target: { value: "+919999900001" } });
  if (email !== null) {
    fireEvent.change(screen.getByTestId("signup-email"), { target: { value: email } });
  }
  await act(async () => {
    fireEvent.click(screen.getByTestId("signup-send-code"));
  });
}

test("send-code passes captcha + phone + name/email metadata to requestPhoneOtp", async () => {
  mockRequestPhoneOtp.mockResolvedValue({ ok: true });
  renderSignup();

  await fillAndSend();
  await waitFor(() => expect(mockExecute).toHaveBeenCalled());
  act(() => cbs.onSuccess("cap-tok"));

  await waitFor(() => expect(mockRequestPhoneOtp).toHaveBeenCalled());
  expect(mockRequestPhoneOtp).toHaveBeenCalledWith("+919999900001", {
    captchaToken: "cap-tok",
    data: { name: "Alice", email: "a@x.com" },
  });
});

test("email is optional — omitted from metadata when blank", async () => {
  mockRequestPhoneOtp.mockResolvedValue({ ok: true });
  renderSignup();
  await fillAndSend({ email: null });
  await waitFor(() => expect(mockExecute).toHaveBeenCalled());
  act(() => cbs.onSuccess("cap"));
  await waitFor(() => expect(mockRequestPhoneOtp).toHaveBeenCalled());
  expect(mockRequestPhoneOtp.mock.calls[0][1].data).toEqual({ name: "Alice" });
});

test("verify creates the account and navigates to signup default", async () => {
  mockRequestPhoneOtp.mockResolvedValue({ ok: true });
  mockVerifyPhoneOtp.mockResolvedValue({ id: "u1", role: "user" });
  renderSignup();
  await fillAndSend();
  await waitFor(() => expect(mockExecute).toHaveBeenCalled());
  act(() => cbs.onSuccess("cap"));

  await screen.findByTestId("signup-otp");
  fireEvent.change(screen.getByTestId("signup-otp"), { target: { value: "123456" } });
  await act(async () => fireEvent.click(screen.getByTestId("signup-verify")));
  await waitFor(() => expect(mockVerifyPhoneOtp).toHaveBeenCalledWith("+919999900001", "123456"));
  expect(mockNavigate).toHaveBeenCalledWith("/app/onboarding/chat?mode=discovery", { replace: true });
});

test("resets Turnstile after send-code failure", async () => {
  mockRequestPhoneOtp.mockRejectedValue(new Error("rate limited"));
  renderSignup();
  await fillAndSend();
  await waitFor(() => expect(mockExecute).toHaveBeenCalled());
  act(() => cbs.onSuccess("cap-tok-2"));
  await screen.findByTestId("signup-error");
  expect(mockReset).toHaveBeenCalled();
});

test("renders ?error= banner from URL on mount", () => {
  renderSignup("/signup?error=signup_failed");
  expect(screen.getByTestId("signup-banner-error").textContent).toMatch(/signup_failed/);
});

test("Google button uses path-only redirectTo", async () => {
  mockLoginWithGoogle.mockResolvedValue({ ok: true });
  renderSignup("/signup?next=%2Fapp%2Fstudy%2Fplan");
  await act(async () => {
    fireEvent.click(screen.getByTestId("signup-google"));
  });
  expect(mockLoginWithGoogle).toHaveBeenCalledWith({ redirectTo: "/app/study/plan" });
});
