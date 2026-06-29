import React, { Suspense, lazy } from "react";
import { Route } from "react-router-dom";
import Landing from "../landingapp";
import FunnelLandingRouter from "../features/funnel/FunnelLandingRouter";
import { GuestOnly } from "../lib/ProtectedRoute";
const Login = lazy(() => import("../pages/auth/Login"));
const Signup = lazy(() => import("../pages/auth/Signup"));
const AuthCallback = lazy(() => import("../pages/auth/AuthCallback"));
const OnboardingChat = lazy(() => import("../pages/OnboardingChat"));
const CopyrightSubmit = lazy(() => import("../pages/CopyrightSubmit"));
const Blogs = lazy(() => import("../pages/Blogs"));
const BlogDetail = lazy(() => import("../pages/BlogDetail"));

const PrototypeRoutes = process.env.REACT_APP_ENABLE_PROTOTYPE === "true"
  ? lazy(() => import("./prototypeRoutes"))
  : null;

export const publicRouteElements = (
  <>
    <Route path="/" element={<Landing />} />
    <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
    <Route path="/signup" element={<GuestOnly><Signup /></GuestOnly>} />
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
