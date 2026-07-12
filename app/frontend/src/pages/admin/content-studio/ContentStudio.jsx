/**
 * Content Studio — the consolidated canonical-content admin surface.
 * Contract: docs/architecture/content-studio.md §3.1/§4.
 *
 * One top-level route, tabs as a query param:
 *   /admin/content-studio?tab=library|review-queue|bulk-import|exam-assignments
 *
 * Content type is a facet (`type=objective_question|writing_prompt`), subject is
 * a filter — this is one content system, not a per-subject product. The
 * objective-question tabs reuse the existing Mock Content pages (their legacy
 * routes now redirect here); the writing-prompt tabs are the new subject-scoped
 * UI over /api/admin/content-studio (handoff:
 * docs/status/ewp-prompt-bank-frontend-handoff.md).
 *
 * Prompt activation (is_active) is a SEPARATE, higher-trust authority
 * (content_studio.activate, EWP-SP2): the Library offers an Activate/Deactivate
 * control only to operators holding that permission, and the server RPC
 * (migration 226) is the sole eligibility authority — the UI never computes
 * eligibility, it only renders the RPC's `{eligible, blockers}` verdict.
 */
import React, { Suspense, lazy } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../../../lib/authContext";
import { studioPerms } from "./permissions";

const MockQuestionList = lazy(() => import("../mocks/QuestionList"));
const MockReviewQueue = lazy(() => import("../mocks/ReviewQueue"));
const MockImportWizard = lazy(() => import("../mocks/ImportWizard"));
const PromptLibrary = lazy(() => import("./PromptLibrary"));
const PromptReviewQueue = lazy(() => import("./PromptReviewQueue"));
const PromptBulkImport = lazy(() => import("./PromptBulkImport"));
const ExamAssignments = lazy(() => import("./ExamAssignments"));
const QuantHeuristicLibrary = lazy(() => import("./QuantHeuristicLibrary"));
const QuantHeuristicReviewQueue = lazy(() => import("./QuantHeuristicReviewQueue"));

const TABS = [
  { id: "library", label: "Library" },
  { id: "review-queue", label: "Review Queue" },
  { id: "bulk-import", label: "Bulk Import" },
  { id: "exam-assignments", label: "Exam Assignments" },
];

const CONTENT_TYPES = [
  { id: "objective_question", label: "Objective questions" },
  { id: "writing_prompt", label: "Writing prompts" },
  { id: "quant_heuristic", label: "Quant heuristics" },
];

export default function ContentStudio() {
  const [params, setParams] = useSearchParams();
  const { user } = useAuth();
  const perms = studioPerms(user);

  const tab = TABS.some((t) => t.id === params.get("tab")) ? params.get("tab") : "library";
  const type = CONTENT_TYPES.some((t) => t.id === params.get("type"))
    ? params.get("type")
    : "objective_question";

  const setParam = (key, value) => {
    const next = new URLSearchParams(params);
    next.set(key, value);
    setParams(next);
  };

  // Library → Exam Assignments deep link: jump to the assignments tab for a
  // specific prompt, carrying its id in the URL (no hand-pasted UUIDs).
  const assignPrompt = (promptId) => {
    const next = new URLSearchParams(params);
    next.set("type", "writing_prompt");
    next.set("tab", "exam-assignments");
    next.set("prompt_id", promptId);
    setParams(next);
  };

  // Tab availability per content type. Exam Assignments only exists for writing
  // prompts. Quant heuristics ship read + review only (migration 243 has no
  // create/bulk/assign RPC), so they expose just Library + Review Queue.
  let typedTabs;
  if (type === "writing_prompt") {
    typedTabs = TABS;
  } else if (type === "quant_heuristic") {
    typedTabs = TABS.filter((t) => t.id === "library" || t.id === "review-queue");
  } else {
    typedTabs = TABS.filter((t) => t.id !== "exam-assignments");
  }
  const activeTab = typedTabs.some((t) => t.id === tab) ? tab : "library";

  // Both writing prompts and quant heuristics are Content Studio content behind
  // the same read gate — hide their bodies without content read permission.
  const needsContentRead = type === "writing_prompt" || type === "quant_heuristic";

  let body = null;
  if (type === "objective_question") {
    if (activeTab === "library") body = <MockQuestionList />;
    else if (activeTab === "review-queue") body = <MockReviewQueue />;
    else body = <MockImportWizard />;
  } else if (type === "quant_heuristic") {
    body = activeTab === "review-queue"
      ? <QuantHeuristicReviewQueue perms={perms} />
      : <QuantHeuristicLibrary perms={perms} />;
  } else if (activeTab === "library") {
    body = <PromptLibrary perms={perms} onAssign={assignPrompt} />;
  } else if (activeTab === "review-queue") {
    body = <PromptReviewQueue perms={perms} />;
  } else if (activeTab === "bulk-import") {
    body = <PromptBulkImport perms={perms} />;
  } else {
    body = <ExamAssignments perms={perms} promptIdParam={params.get("prompt_id") || ""} />;
  }

  return (
    <div data-testid="content-studio">
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 12, padding: "12px 16px 0" }}>
        <div role="tablist" aria-label="Content Studio sections" style={{ display: "flex", gap: 4 }}>
          {typedTabs.map((t) => (
            <button
              key={t.id}
              role="tab"
              type="button"
              aria-selected={activeTab === t.id}
              className={`btn small${activeTab === t.id ? " primary" : ""}`}
              onClick={() => setParam("tab", t.id)}
              data-testid={`content-studio-tab-${t.id}`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <label style={{ marginLeft: "auto", display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12 }}>
          Content type
          <select
            className="input"
            value={type}
            onChange={(e) => setParam("type", e.target.value)}
            data-testid="content-studio-type"
            style={{ width: "auto" }}
          >
            {CONTENT_TYPES.map((t) => (
              <option key={t.id} value={t.id}>{t.label}</option>
            ))}
          </select>
        </label>
      </div>
      {needsContentRead && !perms.canRead ? (
        <div style={{ padding: "2rem", opacity: 0.7 }} data-testid="content-studio-no-access">
          You do not have access to this content. Ask an admin for
          content_studio.author or content_studio.review.
        </div>
      ) : (
        <Suspense fallback={<div style={{ padding: "2rem", opacity: 0.7 }}>Loading…</div>}>
          {body}
        </Suspense>
      )}
    </div>
  );
}
