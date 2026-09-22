/**
 * Which subject the surface opens on.
 *
 * Subject is required context — without it "2025 · P1" names six different
 * papers — so the one thing that must not happen is asking for it every visit.
 * These pin the order it is resolved in, and that an unresolvable subject
 * means a picker rather than a guess.
 */
import {
  clearLastSubject,
  readLastSubject,
  resolveSubject,
  writeLastSubject,
} from "../subjectMemory";

const PSIR = "Political Science and International Relations";

const CATALOG = {
  subjects: [{ subject: PSIR }, { subject: "Anthropology" }],
  papers: [
    { id: "p-psir", subject: PSIR },
    { id: "p-anth", subject: "Anthropology" },
    { id: "p-orphan", subject: null },
  ],
};

beforeEach(() => {
  try {
    window.localStorage.clear();
  } catch {
    /* disabled */
  }
});

// ── the resolution order ───────────────────────────────────────────────────

test("the URL wins — a shared link is an explicit request", () => {
  expect(
    resolveSubject({ urlSubject: "Anthropology", paperId: "p-psir", catalog: CATALOG,
                     lastUsed: PSIR }),
  ).toEqual({ subject: "Anthropology", source: "url" });
});

test("a paper_id in the URL implies its subject", () => {
  expect(
    resolveSubject({ urlSubject: null, paperId: "p-psir", catalog: CATALOG, lastUsed: null }),
  ).toEqual({ subject: PSIR, source: "paper" });
});

test("a paper_id beats the remembered subject", () => {
  /* The link says which paper. Opening it under a different subject would
     show the aspirant a paper that is not in the subject they are looking at. */
  expect(
    resolveSubject({ urlSubject: null, paperId: "p-anth", catalog: CATALOG, lastUsed: PSIR }),
  ).toEqual({ subject: "Anthropology", source: "paper" });
});

test("the last-used subject is next", () => {
  expect(
    resolveSubject({ urlSubject: null, paperId: null, catalog: CATALOG, lastUsed: PSIR }),
  ).toEqual({ subject: PSIR, source: "remembered" });
});

test("one subject needs no picker", () => {
  expect(
    resolveSubject({ urlSubject: null, paperId: null, lastUsed: null,
                     catalog: { subjects: [{ subject: PSIR }], papers: [] } }),
  ).toEqual({ subject: PSIR, source: "only" });
});

test("nothing resolvable means the picker, not a guess", () => {
  expect(
    resolveSubject({ urlSubject: null, paperId: null, catalog: CATALOG, lastUsed: null }),
  ).toEqual({ subject: null, source: "none" });
});

// ── the edges that would otherwise strand the surface ──────────────────────

test("a remembered subject the corpus no longer has is ignored", () => {
  /* Honouring it would gate the surface on a subject that can never be
     picked — the aspirant would see an empty catalogue and no way out. */
  expect(
    resolveSubject({ urlSubject: null, paperId: null, catalog: CATALOG,
                     lastUsed: "Astrophysics" }),
  ).toEqual({ subject: null, source: "none" });
});

test("a paper_id that resolves to nothing falls through rather than stranding", () => {
  expect(
    resolveSubject({ urlSubject: null, paperId: "p-nope", catalog: CATALOG, lastUsed: PSIR }),
  ).toEqual({ subject: PSIR, source: "remembered" });
});

test("a paper with no subject of its own falls through", () => {
  expect(
    resolveSubject({ urlSubject: null, paperId: "p-orphan", catalog: CATALOG, lastUsed: null }),
  ).toEqual({ subject: null, source: "none" });
});

test("a missing catalogue resolves to the picker instead of throwing", () => {
  expect(resolveSubject({ urlSubject: null, paperId: "p1", catalog: null, lastUsed: null }))
    .toEqual({ subject: null, source: "none" });
});

// ── the memory itself ──────────────────────────────────────────────────────

test("a subject is remembered per user", () => {
  writeLastSubject("user-a", PSIR);
  writeLastSubject("user-b", "Anthropology");
  // A shared machine must not hand one aspirant another's optional.
  expect(readLastSubject("user-a")).toBe(PSIR);
  expect(readLastSubject("user-b")).toBe("Anthropology");
});

test("nothing remembered reads as nothing", () => {
  expect(readLastSubject("user-new")).toBeNull();
});

test("an empty subject is not written", () => {
  writeLastSubject("user-a", PSIR);
  writeLastSubject("user-a", "");
  expect(readLastSubject("user-a")).toBe(PSIR);
});

test("clearing forgets it", () => {
  writeLastSubject("user-a", PSIR);
  clearLastSubject("user-a");
  expect(readLastSubject("user-a")).toBeNull();
});

test("storage being unavailable costs the memory, not the surface", () => {
  /* Private windows and some corporate policies throw on localStorage. A
     surface that throws there is worse than one that asks again. */
  const original = Object.getOwnPropertyDescriptor(window, "localStorage");
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    get() {
      throw new Error("access denied");
    },
  });
  try {
    expect(() => writeLastSubject("user-a", PSIR)).not.toThrow();
    expect(readLastSubject("user-a")).toBeNull();
    expect(() => clearLastSubject("user-a")).not.toThrow();
  } finally {
    if (original) Object.defineProperty(window, "localStorage", original);
  }
});
