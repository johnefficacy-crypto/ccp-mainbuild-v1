import React, { lazy } from "react";
import { Navigate, Route, useParams } from "react-router-dom";
import { ProtectedRoute } from "../lib/ProtectedRoute";
import { ADMIN_ROLES } from "../lib/rbac";
import RouteErrorBoundary from "../components/RouteErrorBoundary";

const AdminShell = lazy(() => import("../pages/admin/AdminShell"));
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
const AdminPyqPaperWorkspace = lazy(() => import("../pages/admin/studyos/PyqPaperWorkspace"));
const AdminExamWorkspace = lazy(() => import("../pages/admin/exam-workspace/ExamWorkspace"));
const AdminExamIntelCms = lazy(() => import("../pages/admin/studyos/ExamIntelCms"));
const AdminGuidedExamWizard = lazy(() => import("../pages/admin/studyos/GuidedExamWizard"));
const AdminContentAccessRequests = lazy(() => import("../pages/admin/studyos/ContentAccessRequests"));
const AdminGroupsConsole = lazy(() => import("../pages/admin/community/GroupsConsole"));
const AdminPartnersConsole = lazy(() => import("../pages/admin/community/PartnersConsole"));
const AdminResourcesReviewQueue = lazy(() => import("../pages/admin/community/ResourcesReviewQueue"));
const AdminMockQuestionList = lazy(() => import("../pages/admin/mocks/QuestionList"));
const AdminMockReviewQueue = lazy(() => import("../pages/admin/mocks/ReviewQueue"));
const AdminMockQuestionEditor = lazy(() => import("../pages/admin/mocks/QuestionEditor"));
const AdminMockImportWizard = lazy(() => import("../pages/admin/mocks/ImportWizard"));
const AdminVerificationReports = lazy(() => import("../pages/admin/VerificationReports"));
const AdminReverificationBatches = lazy(() => import("../pages/admin/ReverificationBatches"));
const AdminKnowledgeGovernance = lazy(() => import("../pages/admin/KnowledgeGovernance"));

function AddCycleRedirect() {
  const { exam_id } = useParams();
  return <Navigate to={`/admin/exam-intelligence/workspace/${exam_id}?tab=setup&action=add-cycle`} replace />;
}

export const adminRouteElements = (
  <>
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
    {/* Knowledge governance */}
    <Route element={<RouteErrorBoundary />}>
      <Route path="/admin/knowledge-governance" element={<AdminKnowledgeGovernance />} />
      <Route path="/admin/organizations" element={<AdminOrganizations />} />
      <Route path="/admin/ai-policy" element={<AdminAIPolicy />} />
      <Route path="/admin/persona" element={<AdminPersona />} />
      <Route path="/admin/exam-intelligence" element={<AdminExamIntelligence />} />
      <Route path="/admin/exam-intelligence/cms" element={<AdminExamIntelCms />} />
      <Route path="/admin/exam-intelligence/new" element={<AdminGuidedExamWizard />} />
      <Route path="/admin/exam-intelligence/exams/:exam_id/add-cycle" element={<AddCycleRedirect />} />
      <Route path="/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace" element={<AdminPyqPaperWorkspace />} />
      <Route path="/admin/exam-intelligence/workspace/:exam_id" element={<AdminExamWorkspace />} />
      <Route path="/admin/exam-intelligence/workspace/:exam_id/:cycle_id" element={<AdminExamWorkspace />} />
      <Route path="/admin/exam-eligibility" element={<AdminExamEligibility />} />
    </Route>
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
    <Route path="/admin/study-os/exam-intel-cms" element={<Navigate to="/admin/exam-intelligence/cms" replace />} />
    <Route path="/admin/study-os/content-access" element={<AdminContentAccessRequests />} />
    {/* Mock Content */}
    <Route path="/admin/mocks/questions" element={<AdminMockQuestionList />} />
    <Route path="/admin/mocks/questions/new" element={<AdminMockQuestionEditor />} />
    <Route path="/admin/mocks/questions/:id" element={<AdminMockQuestionEditor />} />
    <Route path="/admin/mocks/review-queue" element={<AdminMockReviewQueue />} />
    <Route path="/admin/mocks/import" element={<AdminMockImportWizard />} />
    {/* Verification reports — exam_intelligence.cms permission checked inside page */}
    <Route element={<RouteErrorBoundary />}>
      <Route path="/admin/verification-reports" element={<AdminVerificationReports />} />
      <Route path="/admin/reverification-batches" element={<AdminReverificationBatches />} />
    </Route>
    </Route>
  </>
);
