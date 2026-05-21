import React from "react";
import { render, screen, waitFor, act } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

const mockGetSession = jest.fn();
const mockApiPost = jest.fn();
const mockPeekAnonymousId = jest.fn();
const mockClearAnonymousId = jest.fn();
const mockPeekMergeClaim = jest.fn();
const mockClearMergeClaim = jest.fn();
const mockToastSuccess = jest.fn();
const mockToastError = jest.fn();

// Hoisted call recorder for exchangeCodeForSession so the test can assert
// that AuthCallback never calls it (detectSessionInUrl=true already did).
const mockExchangeCodeForSession = jest.fn();

jest.mock("../../lib/supabase", () => ({
  __esModule: true,
  supabase: {
    auth: {
      getSession: (...args) => mockGetSession(...args),
      exchangeCodeForSession: (...args) => mockExchangeCodeForSession(...args),
    },
  },
}));

jest.mock("../../lib/api", () => ({
  __esModule: true,
  api: { post: (...args) => mockApiPost(...args) },
}));

jest.mock("../../features/onboarding-chat/anonymousId", () => ({
  __esModule: true,
  peekAnonymousId: (...args) => mockPeekAnonymousId(...args),
  clearAnonymousId: (...args) => mockClearAnonymousId(...args),
}));

jest.mock("../../features/onboarding-chat/mergeClaim", () => ({
  __esModule: true,
  peekMergeClaim: (...args) => mockPeekMergeClaim(...args),
  clearMergeClaim: (...args) => mockClearMergeClaim(...args),
}));

jest.mock("../../shared/ui/ToastProvider", () => ({
  __esModule: true,
  useToast: () => ({ success: mockToastSuccess, error: mockToastError }),
}));

// eslint-disable-next-line global-require
const AuthCallback = require("./AuthCallback").default;

function LoginMarker() {
  // Renders the search string so we can assert the bounce-back error message.
  const search = window.location.search; // jsdom won't track router search, use a sentinel
  return <div data-testid="login-marker">{search}</div>;
}

function NextMarker({ id }) {
  return <div data-testid={id}>landed</div>;
}

function mountAt(url) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/login" element={<LoginMarker />} />
        <Route path="/app" element={<NextMarker id="app-marker" />} />
        <Route path="/app/study/plan" element={<NextMarker id="study-plan" />} />
        <Route path="/app/profile" element={<NextMarker id="profile" />} />
      </Routes>
    </MemoryRouter>,
  );
}

const SESSION = {
  access_token: "jwt-access-token-xyz",
  user: { id: "u1" },
};

beforeEach(() => {
  mockGetSession.mockReset();
  mockApiPost.mockReset();
  mockPeekAnonymousId.mockReset();
  mockClearAnonymousId.mockReset();
  mockExchangeCodeForSession.mockReset();
  mockPeekMergeClaim.mockReset();
  mockClearMergeClaim.mockReset();
  mockToastSuccess.mockReset();
  mockToastError.mockReset();
  mockApiPost.mockResolvedValue({});
  mockPeekAnonymousId.mockReturnValue(null);
  mockPeekMergeClaim.mockReturnValue(null);
});

test("redirects to a safe ?next= path", async () => {
  mockGetSession.mockResolvedValue({ data: { session: SESSION }, error: null });
  mountAt("/auth/callback?next=%2Fapp%2Fstudy%2Fplan");
  await screen.findByTestId("study-plan");
  expect(mockExchangeCodeForSession).not.toHaveBeenCalled();
});

test("rejects protocol-relative next and falls back to /app", async () => {
  mockGetSession.mockResolvedValue({ data: { session: SESSION }, error: null });
  mountAt("/auth/callback?next=%2F%2Fevil.com");
  await screen.findByTestId("app-marker");
});

test("rejects backslash-escaped next and falls back to /app", async () => {
  mockGetSession.mockResolvedValue({ data: { session: SESSION }, error: null });
  mountAt("/auth/callback?next=%2F%5Cevil.com");
  await screen.findByTestId("app-marker");
});

test("rejects percent-encoded protocol-relative next", async () => {
  mockGetSession.mockResolvedValue({ data: { session: SESSION }, error: null });
  mountAt("/auth/callback?next=%2F%252Fevil.com");
  await screen.findByTestId("app-marker");
});

test("OAuth provider error_description routes to /login?error=...", async () => {
  mockGetSession.mockResolvedValue({ data: { session: null }, error: null });
  mountAt(
    "/auth/callback?error=access_denied&error_description=user_cancelled",
  );
  await screen.findByTestId("login-marker");
  expect(mockGetSession).not.toHaveBeenCalled();
});

test("missing session routes to /login?error=auth_session_missing", async () => {
  mockGetSession.mockResolvedValue({ data: { session: null }, error: null });
  mountAt("/auth/callback?next=%2Fapp");
  await screen.findByTestId("login-marker");
});

test("stitches anonymous session with explicit Bearer header", async () => {
  mockGetSession.mockResolvedValue({ data: { session: SESSION }, error: null });
  mockPeekAnonymousId.mockReturnValue("anon_abc");
  mockApiPost.mockResolvedValue({ ok: true });
  mountAt("/auth/callback?next=%2Fapp%2Fstudy%2Fplan");
  await screen.findByTestId("study-plan");

  expect(mockApiPost).toHaveBeenCalledWith(
    "/api/onboarding-unified/stitch-anonymous",
    { anonymous_id: "anon_abc" },
    expect.objectContaining({
      headers: { Authorization: `Bearer ${SESSION.access_token}` },
    }),
  );
  await waitFor(() => expect(mockClearAnonymousId).toHaveBeenCalled());
});

test("stitch failure does not block redirect", async () => {
  mockGetSession.mockResolvedValue({ data: { session: SESSION }, error: null });
  mockPeekAnonymousId.mockReturnValue("anon_xyz");
  mockApiPost.mockRejectedValue(new Error("backend down"));
  mountAt("/auth/callback?next=%2Fapp");
  await screen.findByTestId("app-marker");
  expect(mockClearAnonymousId).not.toHaveBeenCalled();
});

test("stitch timeout does not block redirect", async () => {
  mockGetSession.mockResolvedValue({ data: { session: SESSION }, error: null });
  mockPeekAnonymousId.mockReturnValue("anon_t");
  mockApiPost.mockImplementation(() => new Promise(() => {}));
  mountAt("/auth/callback?next=%2Fapp");
  await screen.findByTestId("app-marker");
});

test("never calls exchangeCodeForSession", async () => {
  mockGetSession.mockResolvedValue({ data: { session: SESSION }, error: null });
  mountAt("/auth/callback?code=oauth_code_value");
  await waitFor(() => expect(mockGetSession).toHaveBeenCalled());
  // Give the effect time to finish.
  await act(async () => {
    await new Promise((r) => setTimeout(r, 0));
  });
  expect(mockExchangeCodeForSession).not.toHaveBeenCalled();
});

test("consumes a merge claim with explicit Bearer header, then clears + toasts", async () => {
  mockGetSession.mockResolvedValue({ data: { session: SESSION }, error: null });
  mockPeekMergeClaim.mockReturnValue("merge_tok_123");
  mockApiPost.mockResolvedValue({ ok: true, merged: {} });
  mountAt("/auth/callback?next=%2Fapp");
  await screen.findByTestId("app-marker");

  expect(mockApiPost).toHaveBeenCalledWith(
    "/api/onboarding/merge-claim/consume",
    { token: "merge_tok_123" },
    expect.objectContaining({
      headers: { Authorization: `Bearer ${SESSION.access_token}` },
    }),
  );
  await waitFor(() => expect(mockClearMergeClaim).toHaveBeenCalled());
  await waitFor(() => expect(mockToastSuccess).toHaveBeenCalled());
});

test("merge-claim consume failure clears token and does not block redirect", async () => {
  mockGetSession.mockResolvedValue({ data: { session: SESSION }, error: null });
  mockPeekMergeClaim.mockReturnValue("merge_tok_bad");
  mockApiPost.mockRejectedValue(new Error("merge failed"));
  mountAt("/auth/callback?next=%2Fapp");
  await screen.findByTestId("app-marker");

  await waitFor(() => expect(mockClearMergeClaim).toHaveBeenCalled());
  await waitFor(() => expect(mockToastError).toHaveBeenCalled());
});

test("no merge claim → consume endpoint is never called", async () => {
  mockGetSession.mockResolvedValue({ data: { session: SESSION }, error: null });
  mountAt("/auth/callback?next=%2Fapp");
  await screen.findByTestId("app-marker");
  expect(mockApiPost).not.toHaveBeenCalledWith(
    "/api/onboarding/merge-claim/consume",
    expect.anything(),
    expect.anything(),
  );
});
