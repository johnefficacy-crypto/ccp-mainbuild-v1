import React from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import EnglishDrills from "./EnglishDrills";
import { ENGLISH_SUBJECT_ID, EXCLUDED_TOPICS, MODULES, MODULE_BY_ID } from "./drillModules";
import { matchArrangement, scopeModules } from "./drillEngine";

jest.mock("../../../shared/config/env", () => ({
  __esModule: true,
  BACKEND_URL: "http://backend.test",
  API_TIMEOUT_MS: 15000,
  ENABLE_DEMO_DATA: false,
}));
jest.mock("../../../lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() } }));
jest.mock("../../../shared/ui/core", () => ({
  useToast: () => ({ success: jest.fn(), error: jest.fn() }),
}));
jest.mock("./drillSound", () => ({ playVerdict: jest.fn(), shake: jest.fn() }));

const { api } = require("../../../lib/api");
const sound = require("./drillSound");

const PJ = MODULE_BY_ID.pj.topics[0].id; // Sentence rearrangement
const SYN = MODULE_BY_ID.voc.topics[0].id; // Synonyms
const ANT = MODULE_BY_ID.voc.topics[1].id; // Antonyms

function topicRow(id, verified, mastery = null) {
  return { topic_id: id, subject_id: ENGLISH_SUBJECT_ID, verified_pyq_count: verified, mastery_score: mastery };
}

const MCQ_ATTEMPT = {
  attempt_id: "att-1",
  status: "in_progress",
  questions: [
    {
      question_id: "q1",
      question_text: "Select the synonym of **Candid**.",
      options: [
        { id: "o1", option_text: "Frank", display_order: 1, source_label: "(a)" },
        { id: "o2", option_text: "Secretive", display_order: 2, source_label: "(b)" },
      ],
      stimuli: [],
      sequence: null,
      selected_option_id: null,
    },
  ],
};

const SEQ = {
  lead: "Arrange the sentences in a logical order.",
  tail: "",
  segments: ["A", "B", "C", "D", "E"].map((l) => ({ label: l, text: `Sentence ${l}.` })),
  option_orders: {
    p1: ["B", "A", "D", "C", "E"],
    p2: ["A", "B", "C", "D", "E"],
    p3: ["E", "D", "C", "B", "A"],
    p4: ["C", "A", "B", "E", "D"],
  },
};

const SEQ_ATTEMPT = {
  attempt_id: "att-2",
  status: "in_progress",
  questions: [
    {
      question_id: "pq1",
      question_text: "Arrange… A. Sentence A. B. Sentence B. …",
      options: ["p1", "p2", "p3", "p4"].map((id, i) => ({ id, option_text: SEQ.option_orders[id].join(""), display_order: i })),
      stimuli: [],
      sequence: SEQ,
      selected_option_id: null,
    },
  ],
};

let routes;
beforeEach(() => {
  jest.clearAllMocks();
  window.localStorage.clear();
  window.scrollTo = jest.fn();
  routes = { get: {}, post: {} };
  // Longest matching prefix wins, so ".../att-1/review" beats ".../att-1".
  const pick = (table, url) =>
    Object.keys(table)
      .filter((k) => url.startsWith(k))
      .sort((a, b) => b.length - a.length)[0];
  api.get.mockImplementation((url) => {
    const hit = pick(routes.get, url);
    if (!hit) return Promise.reject(Object.assign(new Error("404"), { status: 404 }));
    const v = routes.get[hit];
    return typeof v === "function" ? v(url) : Promise.resolve(v);
  });
  api.post.mockImplementation((url, body) => {
    const hit = pick(routes.post, url);
    if (!hit) return Promise.resolve({ ok: true });
    const v = routes.post[hit];
    return typeof v === "function" ? v(url, body) : Promise.resolve(v);
  });
});

function scope(items) {
  routes.get["/api/study/topics"] = { items };
}

// ── the declared mapping ────────────────────────────────────────────────────

test("mapping accounts for all 71 English microtopics exactly once, with no parts-of-speech module", () => {
  const mapped = MODULES.flatMap((m) => m.topics.map((t) => t.id));
  const excluded = EXCLUDED_TOPICS.map((t) => t.id);
  expect(mapped).toHaveLength(58);
  expect(new Set([...mapped, ...excluded]).size).toBe(71);
  expect(mapped.length + excluded.length).toBe(71);
  expect(MODULES.map((m) => m.id)).toEqual(["pj", "err", "imp", "cloze", "rc", "voc", "ce", "sc"]);
  expect(MODULES.find((m) => /parts of speech/i.test(m.name))).toBeUndefined();
  // narration is a topic inside sentence construction, not a module
  expect(MODULE_BY_ID.sc.topics.map((t) => t.label)).toContain("Direct → indirect");
});

test("scopeModules narrows to locked topics and separates the unpractiseable", () => {
  const s = scopeModules([topicRow(SYN, 12, 40), topicRow(ANT, 0)]);
  const voc = s.find((x) => x.module.id === "voc");
  expect(voc.locked.map((t) => t.id)).toEqual([SYN, ANT]);
  expect(voc.practiceable.map((t) => t.id)).toEqual([SYN]);
  expect(voc.verified).toBe(12);
  expect(voc.mastery).toBe(40);
  expect(s.find((x) => x.module.id === "pj").locked).toHaveLength(0);
});

test("arrangement matching is by the option's reviewed order, not by text", () => {
  expect(matchArrangement(SEQ.option_orders, ["B", "A", "D", "C", "E"])).toBe("p1");
  expect(matchArrangement(SEQ.option_orders, ["B", "A", "C", "D", "E"])).toBeNull();
});

// ── scope + honest empty states ────────────────────────────────────────────

test("no locked English coverage renders an honest empty state, never questions", async () => {
  scope([]);
  render(<EnglishDrills />);
  expect(await screen.findByTestId("ed-no-scope")).toHaveTextContent("no locked English Language coverage");
  expect(screen.queryByTestId("ed-module-pj")).toBeNull();
});

test("a module with none of its topics locked names what is missing", async () => {
  scope([topicRow(SYN, 5)]);
  render(<EnglishDrills />);
  const card = await screen.findByTestId("ed-module-pj");
  expect(card).toHaveTextContent("Not in your exam");
  fireEvent.click(card);
  expect(screen.getByTestId("ed-module-empty")).toHaveTextContent("Sentence rearrangement, Logical order");
  expect(screen.queryByTestId("ed-set-start")).toBeNull();
});

test("a locked topic with zero verified questions says so", async () => {
  scope([topicRow(ANT, 0)]);
  render(<EnglishDrills />);
  fireEvent.click(await screen.findByTestId("ed-module-voc"));
  expect(screen.getByTestId("ed-topic-empty")).toHaveTextContent("No verified past-paper questions yet for “Antonyms”");
  expect(screen.getByTestId("ed-not-locked")).toHaveTextContent("Synonyms");
});

test("launch goes through the subject practice endpoint; 409 is an empty state, not an error", async () => {
  scope([topicRow(SYN, 3)]);
  routes.post["/api/study/subjects/"] = () => Promise.reject(Object.assign(new Error("none"), { status: 409 }));
  render(<EnglishDrills />);
  fireEvent.click(await screen.findByTestId("ed-module-voc"));
  fireEvent.click(screen.getByText("Start set →"));
  expect(await screen.findByTestId("ed-set-empty")).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledWith(`/api/study/subjects/${ENGLISH_SUBJECT_ID}/practice/start`, {
    mode: "topic_pyq",
    topic_id: SYN,
  });
});

// ── answer → check → verdict ────────────────────────────────────────────────

test("answers save to the attempt; checking submits, then the verdict buzzes and shows the answer", async () => {
  scope([topicRow(SYN, 1, 20)]);
  routes.post["/api/study/subjects/"] = { kind: "pyq_practice", route: "/x", attempt_id: "att-1" };
  routes.get["/api/study/mocks/attempts/att-1/review"] = {
    questions: [
      {
        question_id: "q1",
        selected_option_id: "o2",
        is_correct: false,
        explanation: "Candid means frank and open.",
        pyq_explanation: null,
        question_snapshot: { ...MCQ_ATTEMPT.questions[0], correct_option_id: "o1" },
      },
    ],
  };
  routes.get["/api/study/mocks/attempts/att-1"] = MCQ_ATTEMPT;
  render(<EnglishDrills />);
  fireEvent.click(await screen.findByTestId("ed-module-voc"));
  fireEvent.click(screen.getByText("Start set →"));
  expect(await screen.findByTestId("ed-answering")).toBeInTheDocument();
  expect(window.localStorage.getItem(`ccp-english-drills:attempt:${SYN}`)).toBe("att-1");

  fireEvent.click(screen.getByTestId("ed-opt-1"));
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith(
      "/api/study/mocks/attempts/att-1/answer",
      expect.objectContaining({ question_id: "q1", selected_option_id: "o2" }),
    ),
  );

  fireEvent.click(screen.getByText(/Check set/));
  expect(await screen.findByTestId("ed-review")).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledWith("/api/study/mocks/attempts/att-1/submit", { claimed_answered_count: 1 });
  expect(screen.getByTestId("ed-feedback")).toHaveTextContent("Not quite — the answer is (a)");
  expect(screen.getByTestId("ed-explanation")).toHaveTextContent("Candid means frank and open.");
  expect(sound.playVerdict).toHaveBeenCalledWith(false);
  expect(sound.shake).toHaveBeenCalled();
  expect(screen.getByTestId("ed-score")).toHaveTextContent("0");
});

// ── parajumbles: N segments from the data ───────────────────────────────────

test("a reviewed parajumble renders all N segments and submits the option naming the order", async () => {
  scope([topicRow(PJ, 1)]);
  routes.post["/api/study/subjects/"] = { attempt_id: "att-2" };
  routes.get["/api/study/mocks/attempts/att-2"] = SEQ_ATTEMPT;
  render(<EnglishDrills />);
  fireEvent.click(await screen.findByTestId("ed-module-pj"));
  fireEvent.click(screen.getByText("Start set →"));
  const list = await screen.findByTestId("ed-pj-list");
  expect(within(list).getAllByRole("button")).toHaveLength(5); // SSC CGL: 5, not a hardcoded 4
  expect(screen.getByTestId("ed-pj-code")).toHaveTextContent("A B C D E");

  // tap-swap C and D → A B D C E: not an option on the paper
  fireEvent.click(screen.getByTestId("ed-pj-row-2"));
  fireEvent.click(screen.getByTestId("ed-pj-row-3"));
  fireEvent.click(screen.getByText("Use this order"));
  expect(screen.getByTestId("ed-pj-note")).toHaveTextContent("isn’t one of the answer choices");

  // swap A and B → B A D C E == option p1
  fireEvent.click(screen.getByTestId("ed-pj-row-0"));
  fireEvent.click(screen.getByTestId("ed-pj-row-1"));
  expect(screen.getByTestId("ed-pj-code")).toHaveTextContent("B A D C E");
  fireEvent.click(screen.getByText("Use this order"));
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith(
      "/api/study/mocks/attempts/att-2/answer",
      expect.objectContaining({ question_id: "pq1", selected_option_id: "p1" }),
    ),
  );
});

test("drag-and-drop moves a segment", async () => {
  scope([topicRow(PJ, 1)]);
  routes.post["/api/study/subjects/"] = { attempt_id: "att-2" };
  routes.get["/api/study/mocks/attempts/att-2"] = SEQ_ATTEMPT;
  render(<EnglishDrills />);
  fireEvent.click(await screen.findByTestId("ed-module-pj"));
  fireEvent.click(screen.getByText("Start set →"));
  await screen.findByTestId("ed-pj-list");
  const dt = { setData: jest.fn(), effectAllowed: "" };
  fireEvent.dragStart(screen.getByTestId("ed-pj-row-4"), { dataTransfer: dt });
  fireEvent.dragOver(screen.getByTestId("ed-pj-row-0"), { dataTransfer: dt });
  fireEvent.drop(screen.getByTestId("ed-pj-row-0"), { dataTransfer: dt });
  expect(screen.getByTestId("ed-pj-code")).toHaveTextContent("E A B C D");
});

test("a parajumble without a reviewed order falls back to plain MCQ", async () => {
  scope([topicRow(PJ, 1)]);
  routes.post["/api/study/subjects/"] = { attempt_id: "att-3" };
  routes.get["/api/study/mocks/attempts/att-3"] = {
    ...SEQ_ATTEMPT,
    attempt_id: "att-3",
    questions: [{ ...SEQ_ATTEMPT.questions[0], sequence: null }],
  };
  render(<EnglishDrills />);
  fireEvent.click(await screen.findByTestId("ed-module-pj"));
  fireEvent.click(screen.getByText("Start set →"));
  expect(await screen.findByTestId("ed-mcq-fallback")).toBeInTheDocument();
  expect(screen.queryByTestId("ed-pj-list")).toBeNull();
  expect(screen.getAllByTestId(/^ed-opt-/)).toHaveLength(4);
});

// ── account is the source of truth; the device only remembers the attempt id

test("reopening resumes the server copy of an in-progress set", async () => {
  scope([topicRow(SYN, 1)]);
  window.localStorage.setItem(`ccp-english-drills:attempt:${SYN}`, "att-1");
  routes.get["/api/study/mocks/attempts/att-1"] = {
    ...MCQ_ATTEMPT,
    questions: [{ ...MCQ_ATTEMPT.questions[0], selected_option_id: "o1" }],
  };
  render(<EnglishDrills />);
  fireEvent.click(await screen.findByTestId("ed-module-voc"));
  expect(await screen.findByTestId("ed-answering")).toBeInTheDocument();
  expect(screen.getByTestId("ed-opt-0")).toHaveAttribute("aria-pressed", "true");
  expect(api.post).not.toHaveBeenCalled();
});

test("a stale resume pointer is dropped and the set can start fresh", async () => {
  scope([topicRow(SYN, 1)]);
  window.localStorage.setItem(`ccp-english-drills:attempt:${SYN}`, "gone");
  render(<EnglishDrills />);
  fireEvent.click(await screen.findByTestId("ed-module-voc"));
  expect(await screen.findByTestId("ed-set-start")).toBeInTheDocument();
  await act(async () => {});
  expect(window.localStorage.getItem(`ccp-english-drills:attempt:${SYN}`)).toBeNull();
});
