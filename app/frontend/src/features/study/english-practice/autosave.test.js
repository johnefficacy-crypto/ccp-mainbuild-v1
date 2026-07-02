import { clearDraft, draftKey, loadDraft, saveDraft } from "./autosave";

describe("autosave", () => {
  beforeEach(() => window.sessionStorage.clear());

  test("draftKey is keyed by session id and unit number", () => {
    expect(draftKey("S1", 2)).toBe("ewp:draft:S1:2");
    expect(draftKey("S1", 2)).not.toBe(draftKey("S2", 2));
    expect(draftKey("S1", 2)).not.toBe(draftKey("S1", 3));
  });

  test("save then load round-trips", () => {
    saveDraft("S1", 1, "in progress");
    expect(loadDraft("S1", 1)).toBe("in progress");
  });

  test("clear removes the draft", () => {
    saveDraft("S1", 1, "in progress");
    clearDraft("S1", 1);
    expect(loadDraft("S1", 1)).toBeNull();
  });

  test("load returns null for an unknown key", () => {
    expect(loadDraft("nope", 9)).toBeNull();
  });
});
