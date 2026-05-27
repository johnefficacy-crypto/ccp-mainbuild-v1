import React, { Suspense, lazy } from "react";
import { Navigate, Route } from "react-router-dom";
import { ProtectedRoute } from "../lib/ProtectedRoute";
import { ADMIN_ROLES } from "../lib/rbac";
import { LoadingSkeleton } from "../shared/ui";
import AdminShell from "../pages/admin/AdminShell";

const AdminOverview = lazy(() => import("../pages/admin/Overview"));
const AdminRecruitments = lazy(() => import("../pages/admin/Recruitments"));
const AdminOperationsConsole = lazy(() => import("../pages/admin/OperationsConsole"));
const AdminEligibilityOps = lazy(() => import("../pages/admin/EligibilityOps"));
const AdminSources = lazy(() => import("../pages/admin/Sources"));
const AdminOrganizations = lazy(() => import("../pages/admin/Organizations"));
const AdminScraper = lazy(() => import("../pages/admin/Scraper"));
const AdminNotifications = lazy(() => import("../pages/admin/Notifications"));
const AdminMarketplace = lazy(() => import("../pages/admin/Marketplace"));
const AdminPlans = lazy(() => import("../pages/admin/Plans"));
const AdminAudit = lazy(() => import("../pages/admin/Audit"));
const AdminRBAC = lazy(() => import("../pages/admin/RBAC"));
const AdminMentorsPg = lazy(() => import("../pages/admin/Mentors"));
const AdminCommunity = lazy(() => import("../pages/admin/Community"));
const AdminAIPolicy = lazy(() => import("../pages/admin/AIPolicy"));
const AdminPersona = lazy(() => import("../pages/admin/Persona"));
const AdminExamIntelligence = lazy(() => import("../pages/admin/ExamIntelligence"));
const AdminExamEligibility = lazy(() => import("../pages/admin/ExamEligibility"));
const AdminModerationQueue = lazy(() => import("../pages/admin/ModerationQueue"));
const AdminKPIs = lazy(() => import("../pages/admin/KPIs"));
const AdminCopyright = lazy(() => import("../pages/admin/Copyright"));
const AdminBlogs = lazy(() => import("../pages/admin/Blogs"));
const AdminUserStudyInspector = lazy(() => import("../pages/admin/studyos/UserStudyInspector"));
const AdminStudyOsPlanOps = lazy(() => import("../pages/admin/studyos/PlanOps"));
const AdminStudyOsArtifacts = lazy(() => import("../pages/admin/studyos/Artifacts"));
const AdminStudyOsMockTrust = lazy(() => import("../pages/admin/studyos/MockTrust"));
const AdminStudyOsReports = lazy(() => import("../pages/admin/studyos/Reports"));
const AdminStudyOsSocial = lazy(() => import("../pages/admin/studyos/Social"));
const AdminExamIntelCms = lazy(() => import("../pages/admin/studyos/ExamIntelCms"));
const AdminContentAccessRequests = lazy(() => import("../pages/admin/studyos/ContentAccessRequests"));
const AdminGroupsConsole = lazy(() => import("../pages/admin/community/GroupsConsole"));
const AdminPartnersConsole = lazy(() => import("../pages/admin/community/PartnersConsole"));
const AdminResourcesReviewQueue = lazy(() => import("../pages/admin/community/ResourcesReviewQueue"));
const AdminMockQuestionList = lazy(() => import("../pages/admin/mocks/QuestionList"));
const AdminMockReviewQueue = lazy(() => import("../pages/admin/mocks/ReviewQueue"));
const AdminMockQuestionEditor = lazy(() => import("../pages/admin/mocks/QuestionEditor"));
const AdminMockImportWizard = lazy(() => import("../pages/admin/mocks/ImportWizard"));

export const adminRouteElements = (
  <Suspense fallback={<LoadingSkeleton />}>
    <Route element={<ProtectedRoute role={ADMIN_ROLES} requireBackend><AdminShell /></ProtectedRoute>}>
    <Route path="/admin" element={<AdminOverview />} />
    <Route path="/admin/operations" element={<AdminOperationsConsole />} />
    <Route path="/admin/recruitments" element={<AdminRecruitments />} />
    {/* Candidate review is now part of the single pipeline workspace. Both
        the old promotion-queue and eligibility-queue deep links funnel into
        the Review & publish surface so there is exactly one place to verify
        and promote scraped candidates. */}
    <Route path="/admin/eligibility-queue" element={<Navigate to="/admin/operations?mode=queue" replace />} />
    <Route path="/admin/promotion-queue" element={<Navigate to="/admin/operations?mode=queue" replace />} />
    <Route path="/admin/eligibility-ops" element={<AdminEligibilityOps />} />
    <Route path="/admin/sources" element={<AdminSources />} />
    <Route path="/admin/organizations" element={<AdminOrganizations />} />
    <Route path="/admin/scraper" element={<AdminScraper />} />
    <Route path="/admin/notifications" element={<AdminNotifications />} />
    <Route path="/admin/marketplace" element={<AdminMarketplace />} />
    <Route path="/admin/plans" element={<AdminPlans />} />
    <Route path="/admin/audit" element={<AdminAudit />} />
    <Route path="/admin/rbac" element={<AdminRBAC />} />
    <Route path="/admin/mentors" element={<AdminMentorsPg />} />
    <Route path="/admin/community" element={<AdminCommunity />} />
    <Route path="/admin/community/groups" element={<AdminGroupsConsole />} />
    <Route path="/admin/community/partners" element={<AdminPartnersConsole />} />
    <Route path="/admin/community/resources" element={<AdminResourcesReviewQueue />} />
    <Route path="/admin/ai-policy" element={<AdminAIPolicy />} />
    <Route path="/admin/persona" element={<AdminPersona />} />
    <Route path="/admin/exam-intelligence" element={<AdminExamIntelligence />} />
    <Route path="/admin/exam-eligibility" element={<AdminExamEligibility />} />
    <Route path="/admin/moderation" element={<AdminModerationQueue />} />
    <Route path="/admin/kpis" element={<AdminKPIs />} />
    <Route path="/admin/copyright" element={<AdminCopyright />} />
    <Route path="/admin/blogs" element={<AdminBlogs />} />
    <Route path="/admin/study-os" element={<AdminUserStudyInspector />} />
    <Route path="/admin/study-os/plan-ops" element={<AdminStudyOsPlanOps />} />
    <Route path="/admin/study-os/artifacts" element={<AdminStudyOsArtifacts />} />
    <Route path="/admin/study-os/mocks" element={<AdminStudyOsMockTrust />} />
    <Route path="/admin/study-os/reports" element={<AdminStudyOsReports />} />
    <Route path="/admin/study-os/social" element={<AdminStudyOsSocial />} />
    <Route path="/admin/study-os/exam-intel-cms" element={<AdminExamIntelCms />} />
    <Route path="/admin/study-os/content-access" element={<AdminContentAccessRequests />} />
    {/* Mock Content */}
    <Route path="/admin/mocks/questions" element={<AdminMockQuestionList />} />
    <Route path="/admin/mocks/questions/new" element={<AdminMockQuestionEditor />} />
    <Route path="/admin/mocks/questions/:id" element={<AdminMockQuestionEditor />} />
    <Route path="/admin/mocks/review-queue" element={<AdminMockReviewQueue />} />
    <Route path="/admin/mocks/import" element={<AdminMockImportWizard />} />
    </Route>
  </Suspense>
);
