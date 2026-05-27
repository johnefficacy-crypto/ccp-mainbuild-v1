import React, { Suspense, lazy } from "react";
import { Route } from "react-router-dom";
import Landing from "../landingapp";
import Login from "../pages/auth/Login";
import Signup from "../pages/auth/Signup";
import ForgotPassword from "../pages/auth/ForgotPassword";
import ResetPassword from "../pages/auth/ResetPassword";
import AuthCallback from "../pages/auth/AuthCallback";
import OnboardingChat from "../pages/OnboardingChat";
import FunnelLandingRouter from "../features/funnel/FunnelLandingRouter";
import { GuestOnly } from "../lib/ProtectedRoute";
import CopyrightSubmit from "../pages/CopyrightSubmit";
import Blogs from "../pages/Blogs";
import BlogDetail from "../pages/BlogDetail";

const PrototypeRoutes = process.env.REACT_APP_ENABLE_PROTOTYPE === "true"
  ? lazy(() => import("./prototypeRoutes"))
  : null;

export const publicRouteElements = (
  <>
    <Route path="/" element={<Landing />} />
    <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
    <Route path="/signup" element={<GuestOnly><Signup /></GuestOnly>} />
    <Route path="/forgot-password" element={<ForgotPassword />} />
    <Route path="/reset-password" element={<ResetPassword />} />
    <Route path="/auth/callback" element={<AuthCallback />} />
    <Route path="/copyright" element={<CopyrightSubmit />} />
    <Route path="/dmca" element={<CopyrightSubmit />} />
    <Route path="/app/onboarding/chat" element={<OnboardingChat />} />
    <Route path="/blog" element={<Blogs />} />
    <Route path="/blog/:slug" element={<BlogDetail />} />
    <Route path="/go/:intent/:recruitmentSlug" element={<FunnelLandingRouter />} />
    <Route path="/go/:intent/:recruitmentSlug/:postSlug" element={<FunnelLandingRouter />} />
    {PrototypeRoutes && <Suspense fallback={null}><PrototypeRoutes /></Suspense>}
  </>
);
