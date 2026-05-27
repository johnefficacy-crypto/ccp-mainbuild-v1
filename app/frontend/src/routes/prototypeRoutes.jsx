import React, { lazy } from "react";
import { Route } from "react-router-dom";

const PrototypeIndex = lazy(() => import("../prototype/PrototypeIndex"));
const PrototypeEligibility = lazy(() => import("../prototype/screens/Eligibility"));
const PrototypeGroups = lazy(() => import("../prototype/screens/Groups"));
const PrototypeResources = lazy(() => import("../prototype/screens/Resources"));
const PrototypeLibrary = lazy(() => import("../prototype/screens/Library"));
const PrototypeSeller = lazy(() => import("../prototype/screens/Seller"));
const PrototypeOnboarding = lazy(() => import("../prototype/screens/Onboarding"));
const PrototypeAdminEligibility = lazy(() => import("../prototype/screens/AdminEligibility"));
const PrototypeAdminCommunity = lazy(() => import("../prototype/screens/AdminCommunity"));
const PrototypeAdminMarket = lazy(() => import("../prototype/screens/AdminMarket"));
const PrototypeAdminFunnel = lazy(() => import("../prototype/screens/AdminFunnel"));
const PrototypeHandoff = lazy(() => import("../prototype/screens/Handoff"));

export default function PrototypeRoutes() {
  return (
    <>
      <Route path="/prototype" element={<PrototypeIndex />} />
      <Route path="/prototype/eligibility" element={<PrototypeEligibility />} />
      <Route path="/prototype/groups" element={<PrototypeGroups />} />
      <Route path="/prototype/resources" element={<PrototypeResources />} />
      <Route path="/prototype/library" element={<PrototypeLibrary />} />
      <Route path="/prototype/seller" element={<PrototypeSeller />} />
      <Route path="/prototype/onboarding" element={<PrototypeOnboarding />} />
      <Route path="/prototype/admin-eligibility" element={<PrototypeAdminEligibility />} />
      <Route path="/prototype/admin-community" element={<PrototypeAdminCommunity />} />
      <Route path="/prototype/admin-marketplace" element={<PrototypeAdminMarket />} />
      <Route path="/prototype/admin-funnel" element={<PrototypeAdminFunnel />} />
      <Route path="/prototype/handoff" element={<PrototypeHandoff />} />
    </>
  );
}
