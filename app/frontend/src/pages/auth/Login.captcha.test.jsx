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
const Login = require("./Login").default;

function renderLogin(path = "/login") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Login />
    </MemoryRouter>,
  );
}

async function sendCode(phone = "+919999900001") {
  fireEvent.change(screen.getByTestId("login-phone"), { target: { value: phone } });
  await act(async () => {
    fireEvent.click(screen.getByTestId("login-send-code"));
  });
}

test("send-code passes captchaToken + E.164 phone to requestPhoneOtp", async () => {
  mockRequestPhoneOtp.mockResolvedValue({ ok: true });
  renderLogin();

  await sendCode("+919999900001");
  await waitFor(() => expect(mockExecute).toHaveBeenCalled());
  act(() => cbs.onSuccess("captcha-A"));

  await waitFor(() => expect(mockRequestPhoneOtp).toHaveBeenCalled());
  expect(mockRequestPhoneOtp).toHaveBeenCalledWith("+919999900001", { captchaToken: "captcha-A" });
});

test("bare 10-digit number is normalized to +91 E.164", async () => {
  mockRequestPhoneOtp.mockResolvedValue({ ok: true });
  renderLogin();
  await sendCode("9999900001");
  await waitFor(() => expect(mockExecute).toHaveBeenCalled());
  act(() => cbs.onSuccess("cap"));
  await waitFor(() => expect(mockRequestPhoneOtp).toHaveBeenCalled());
  expect(mockRequestPhoneOtp.mock.calls[0][0]).toBe("+919999900001");
});

test("verify step calls verifyPhoneOtp and role-redirects", async () => {
  mockRequestPhoneOtp.mockResolvedValue({ ok: true });
  mockVerifyPhoneOtp.mockResolvedValue({ role: "user" });
  renderLogin();

  await sendCode();
  await waitFor(() => expect(mockExecute).toHaveBeenCalled());
  act(() => cbs.onSuccess("cap"));
  await waitFor(() => expect(mockRequestPhoneOtp).toHaveBeenCalled());

  await screen.findByTestId("login-otp");
  fireEvent.change(screen.getByTestId("login-otp"), { target: { value: "123456" } });
  await act(async () => {
    fireEvent.click(screen.getByTestId("login-verify"));
  });
  await waitFor(() => expect(mockVerifyPhoneOtp).toHaveBeenCalledWith("+919999900001", "123456"));
  expect(mockNavigate).toHaveBeenCalledWith("/app", { replace: true });
});

test("admin role redirects to /admin after verify", async () => {
  mockRequestPhoneOtp.mockResolvedValue({ ok: true });
  mockVerifyPhoneOtp.mockResolvedValue({ role: "super_admin" });
  renderLogin();
  await sendCode();
  await waitFor(() => expect(mockExecute).toHaveBeenCalled());
  act(() => cbs.onSuccess("cap"));
  await screen.findByTestId("login-otp");
  fireEvent.change(screen.getByTestId("login-otp"), { target: { value: "123456" } });
  await act(async () => fireEvent.click(screen.getByTestId("login-verify")));
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/admin", { replace: true }));
});

test("invalid phone shows an error and does not call requestPhoneOtp", async () => {
  renderLogin();
  await sendCode("123");
  await screen.findByTestId("login-error");
  expect(mockRequestPhoneOtp).not.toHaveBeenCalled();
});

test("renders ?error= banner from URL on mount", () => {
  renderLogin("/login?error=oauth_failed");
  expect(screen.getByTestId("login-banner-error").textContent).toMatch(/oauth_failed/);
});

test("Google button passes path-only redirectTo to loginWithGoogle", async () => {
  mockLoginWithGoogle.mockResolvedValue({ ok: true });
  renderLogin("/login?next=%2Fapp%2Fstudy%2Fplan");
  await act(async () => {
    fireEvent.click(screen.getByTestId("login-google"));
  });
  expect(mockLoginWithGoogle).toHaveBeenCalledWith({ redirectTo: "/app/study/plan" });
});
