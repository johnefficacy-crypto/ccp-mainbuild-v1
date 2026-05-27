import { createClient } from "@supabase/supabase-js";
import { readEnv } from "./env";
import { getAccessToken } from "./seedUser";

/**
 * Attempt factory. Builds attempts through the REAL backend API so scoring and
 * analytics derivation run exactly as in production — we never hand-write
 * mock_attempt_* rows. Combined with resetAttempts() this gives an idempotent
 * "truncate-and-seed" per run: state never drifts across re-runs.
 *
 * Convention from app/supabase/seeds/e2e_fixtures.sql: option_index 1 is always
 * the correct option, so the factory can deterministically make a question
 * correct (pick index 1), wrong (pick index 2), or unattempted (skip).
 */
type AttemptQuestion = {
  question_id: string;
  section_index: number | null;
  options: { id: string; option_index: number }[];
  selected_option_id?: string | null;
};

let _env: ReturnType<typeof readEnv> | null = null;
const env = () => (_env ??= readEnv());

async function apiCall(method: string, path: string, token: string, body?: unknown) {
  const res = await fetch(`${env().backendURL}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${method} ${path} → ${res.status}: ${text}`);
  }
  return res.status === 204 ? null : res.json();
}

/** Delete the seeded user's attempts on the E2E template (cascades responses). */
export async function resetAttempts(userId: string): Promise<void> {
  const admin = createClient(env().supabaseURL, env().supabaseServiceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
  const { data: tmpl } = await admin
    .from("mock_templates")
    .select("id")
    .eq("slug", env().templateSlug)
    .maybeSingle();
  if (!tmpl) {
    throw new Error(
      `Template "${env().templateSlug}" not found. Apply app/supabase/seeds/e2e_fixtures.sql first.`,
    );
  }
  await admin.from("mock_attempts").delete().eq("user_id", userId).eq("template_id", tmpl.id);
}

export async function startAttempt(token: string): Promise<string> {
  const data = await apiCall("POST", "/api/study/mocks/attempts/start", token, {
    template_slug: env().templateSlug,
  });
  return data.attempt_id;
}

async function getAttempt(token: string, attemptId: string): Promise<AttemptQuestion[]> {
  const data = await apiCall("GET", `/api/study/mocks/attempts/${attemptId}`, token);
  return data.questions || [];
}

function optionByIndex(q: AttemptQuestion, index: number): string | null {
  return q.options.find((o) => o.option_index === index)?.id ?? null;
}

export type AnswerOutcome = "correct" | "wrong" | "unattempted";

/**
 * Start an attempt and answer each question per `plan` (cycled if shorter than
 * the question count), respecting section locks by entering each section in
 * order before answering its questions. `markEvery` marks every Nth question
 * for review. Submits and returns the attempt id.
 */
export async function seedSubmittedAttempt(opts: {
  plan?: AnswerOutcome[];
  markEvery?: number;
} = {}): Promise<string> {
  const plan = opts.plan ?? ["correct", "wrong", "unattempted"];
  const markEvery = opts.markEvery ?? 0;
  const token = await getAccessToken();
  const attemptId = await startAttempt(token);
  const questions = await getAttempt(token, attemptId);

  const sections = [...new Set(questions.map((q) => Number(q.section_index ?? 0)))].sort(
    (a, b) => a - b,
  );

  let i = 0;
  for (const section of sections) {
    await apiCall("POST", `/api/study/mocks/attempts/${attemptId}/enter-section`, token, {
      section_index: section,
    });
    const inSection = questions.filter((q) => Number(q.section_index ?? 0) === section);
    for (const q of inSection) {
      const outcome = plan[i % plan.length];
      const marked = markEvery > 0 && (i + 1) % markEvery === 0;
      if (outcome !== "unattempted") {
        await apiCall("POST", `/api/study/mocks/attempts/${attemptId}/answer`, token, {
          question_id: q.question_id,
          selected_option_id: optionByIndex(q, outcome === "correct" ? 1 : 2),
          is_marked_for_review: marked,
          client_seq: i + 1,
          time_spent_sec: 5,
        });
      } else if (marked) {
        await apiCall("POST", `/api/study/mocks/attempts/${attemptId}/answer`, token, {
          question_id: q.question_id,
          selected_option_id: null,
          is_marked_for_review: true,
          client_seq: i + 1,
          time_spent_sec: 2,
        });
      }
      i += 1;
    }
  }

  await apiCall("POST", `/api/study/mocks/attempts/${attemptId}/submit`, token, {});
  return attemptId;
}

/** Seed N submitted attempts (Flow 3 needs a 5-point trend). Returns ids in order. */
export async function seedSubmittedAttempts(n: number, userId: string): Promise<string[]> {
  await resetAttempts(userId);
  const ids: string[] = [];
  for (let k = 0; k < n; k += 1) {
    // Vary the mix per attempt so the trend line actually moves.
    const correctBias = k % 3;
    const plan: AnswerOutcome[] =
      correctBias === 0
        ? ["correct", "wrong", "correct"]
        : correctBias === 1
        ? ["correct", "correct", "wrong"]
        : ["wrong", "correct", "unattempted"];
    ids.push(await seedSubmittedAttempt({ plan, markEvery: 4 }));
  }
  return ids;
}
