import React, {lazy } from "react";
import { Navigate, Route } from "react-router-dom";
import RouteErrorBoundary from "../components/RouteErrorBoundary";
import { ProtectedRoute } from "../lib/ProtectedRoute";

const CommunityScreen = lazy(() => import("../features/community/CommunityScreen"));
const StudyGroupsScreen = lazy(() => import("../features/community/StudyGroupsScreen"));
const PartnersScreen = lazy(() => import("../features/community/PartnersScreen"));
const MentorsScreen = lazy(() => import("../features/community/MentorsScreen"));
const ResourcesScreen = lazy(() => import("../features/community/ResourcesScreen"));

const Today = lazy(() => import("../pages/Today"));
const DashShell = lazy(() => import("../pages/DashShell"));
const Profile = lazy(() => import("../pages/Profile"));
const ExamDetail = lazy(() => import("../pages/ExamDetail"));
const ExamDetailRedirect = lazy(() => import("../pages/ExamDetailRedirect"));
const Saved = lazy(() => import("../pages/Saved"));
const StudyPlan = lazy(() => import("../pages/StudyPlan"));
const Focus = lazy(() => import("../pages/study/Focus"));
const Mocks = lazy(() => import("../pages/study/Mocks"));
const EnglishPracticeShell = lazy(() => import("../pages/study/EnglishPracticeShell"));
const ErrorLab = lazy(() => import("../pages/study/ErrorLab"));
const Subjects = lazy(() => import("../pages/study/Subjects"));
const WeeklyReview = lazy(() => import("../pages/study/WeeklyReview"));
const StudyCompare = lazy(() => import("../pages/study/Compare"));
const Notes = lazy(() => import("../pages/Notes"));
const Flashcards = lazy(() => import("../pages/study/Flashcards"));
const FlashcardsDeck = lazy(() => import("../pages/study/FlashcardsDeck"));
const Mistakes = lazy(() => import("../pages/study/Mistakes"));
const Revision = lazy(() => import("../pages/study/Revision"));
const Reports = lazy(() => import("../pages/Reports"));
const Marketplace = lazy(() => import("../pages/Marketplace"));
const ResourceDetail = lazy(() => import("../pages/ResourceDetail"));
const CoursePlayer = lazy(() => import("../pages/CoursePlayer"));
const MentorDetail = lazy(() => import("../pages/MentorDetail"));
const AIChat = lazy(() => import("../pages/AIChat"));
const Notifications = lazy(() => import("../pages/Notifications"));
const NotificationPreferences = lazy(() => import("../pages/NotificationPreferences"));
const Pricing = lazy(() => import("../pages/Pricing"));
const EligibilityShell = lazy(() => import("../pages/eligibility/EligibilityShell"));
const EligibleExamsPage = lazy(() => import("../pages/eligibility/EligibleExamsPage"));
const EligibleRecruitmentsPage = lazy(() => import("../pages/eligibility/EligibleRecruitmentsPage"));
const EligibilityTrackerPage = lazy(() => import("../pages/eligibility/EligibilityTrackerPage"));
const StudyShell = lazy(() => import("../pages/study/StudyShell"));
const StudyHome = lazy(() => import("../pages/study/StudyHome"));
const StudyLearningHub = lazy(() => import("../pages/study/StudyLearningHub"));
const StudyProgressHub = lazy(() => import("../pages/study/StudyProgressHub"));
const AttemptShellRouter = lazy(() => import("../pages/study/mocks/AttemptShellRouter"));
const MockResult = lazy(() => import("../pages/study/mocks/MockResult"));
const MockReview = lazy(() => import("../pages/study/mocks/MockReview"));

export const appRouteElements = (
  <>
    <Route element={<ProtectedRoute requireBackend><DashShell /></ProtectedRoute>}>
    <Route element={<RouteErrorBoundary />}>
      <Route path="/app" element={<Navigate to="/app/today" replace />} />
      <Route path="/app/dashboard" element={<Navigate to="/app/today" replace />} />
      <Route path="/app/today" element={<Today />} />
      <Route path="/app/profile" element={<Profile />} />
      <Route path="/app/onboarding" element={<Navigate to="/app/onboarding/chat?mode=discovery" replace />} />
      <Route path="/app/saved" element={<Saved />} />

      {/*
        Canonical aspirant areas.

        Param convention:
          :slug  on /eligibility/exams/:slug      — stable catalogue entity.
          :id    on /eligibility/recruitments/:id — transient cycle entity
                                                    keyed by DB id.
      */}
      <Route path="/app/eligibility" element={<EligibilityShell />}>
        <Route index element={<Navigate to="/app/eligibility/exams" replace />} />
        <Route path="exams" element={<EligibleExamsPage />} />
        {/* Exam intelligence detail moved to the top-level Exam Intelligence
            surface (item 13). Old link kept as a redirect so nothing breaks. */}
        <Route path="exams/:slug" element={<ExamDetailRedirect />} />
        <Route path="recruitments" element={<EligibleRecruitmentsPage />} />
        <Route path="recruitments/:id" element={<EligibleRecruitmentsPage />} />
        <Route path="tracker" element={<EligibilityTrackerPage />} />
      </Route>

      {/* Top-level Exam Intelligence surface (item 13). Landing = exam
          catalogue; detail = the intelligence-focused exam page. */}
      <Route path="/app/exam-intelligence" element={<EligibleExamsPage />} />
      <Route path="/app/exam-intelligence/exams/:slug" element={<ExamDetail />} />

      <Route path="/app/study" element={<StudyShell />}>
        <Route index element={<StudyHome />} />
        <Route path="plan" element={<StudyPlan />} />
        <Route path="learning" element={<StudyLearningHub />} />
        <Route path="progress" element={<StudyProgressHub />} />
        {/* English Writing Practice (EWP-3): mounted UNDER StudyShell + inside
            RouteErrorBoundary per the design lock. Entered via planner tasks; not
            an attempt-shell route; absent from the sidebar (no-new-surface rule). */}
        <Route path="practice/english/:sessionId" element={<EnglishPracticeShell />} />
        {/* Error Lab (EWP-4): recurring writing issues grouped by microtopic.
            Mounted UNDER StudyShell + inside RouteErrorBoundary like the EWP-3
            route; absent from the sidebar (no-new-surface rule). */}
        <Route path="error-lab" element={<ErrorLab />} />
      </Route>
      <Route path="/app/study/focus" element={<Focus />} />
      <Route path="/app/study/mocks" element={<Mocks />} />
      <Route path="/app/study/mocks/attempts/:attemptId" element={<AttemptShellRouter />} />
      <Route path="/app/study/mocks/attempts/:attemptId/result" element={<MockResult />} />
      <Route path="/app/study/mocks/attempts/:attemptId/review" element={<MockReview />} />
      <Route path="/app/study/subjects" element={<Subjects />} />
      <Route path="/app/study/review" element={<WeeklyReview />} />
      <Route path="/app/study/compare" element={<StudyCompare />} />
      <Route path="/app/notes" element={<Notes />} />
      <Route path="/app/flashcards" element={<Flashcards />} />
      <Route path="/app/flashcards/:deckId" element={<FlashcardsDeck />} />
      <Route path="/app/study/mistakes" element={<Mistakes />} />
      <Route path="/app/study/resources" element={<ResourcesScreen />} />
      <Route path="/app/study/revision" element={<Revision />} />
      <Route path="/app/reports" element={<Reports />} />
      <Route path="/app/community" element={<CommunityScreen />} />
      <Route path="/app/community/:spaceId" element={<CommunityScreen />} />
      <Route path="/app/community/:spaceId/:channelId" element={<CommunityScreen />} />
      <Route path="/app/community/:spaceId/:channelId/:threadId" element={<CommunityScreen />} />
      <Route path="/app/groups" element={<StudyGroupsScreen />} />
      <Route path="/app/partners" element={<PartnersScreen />} />
      <Route path="/app/resources" element={<ResourcesScreen />} />
      <Route path="/app/marketplace" element={<Marketplace />} />
      <Route path="/app/marketplace/:id" element={<ResourceDetail />} />
      <Route path="/app/marketplace/:id/learn" element={<CoursePlayer />} />
      <Route path="/app/mentors" element={<MentorsScreen />} />
      <Route path="/app/mentors/:id" element={<MentorDetail />} />
      <Route path="/app/accountability" element={<PartnersScreen />} />
      <Route path="/app/ai" element={<AIChat />} />
      <Route path="/app/notifications" element={<Notifications />} />
      <Route path="/app/notifications/preferences" element={<NotificationPreferences />} />
      <Route path="/app/pricing" element={<Pricing />} />
    </Route>
    </Route>
  </>
);
