import {
  UNGROUPED,
  buildTree,
  firstNode,
  positionOf,
  sameNode,
  searchTopics,
  topicsForNode,
} from "./syllabusTree";

function topic(over) {
  return {
    topic_id: "t1",
    topic: "Percentage",
    subject_id: "s1",
    subject: "Quantitative Aptitude",
    parent_topic_id: "m1",
    parent_topic: "Quantitative methods",
    selection_kind: "compulsory",
    predictability_band: null,
    scheduled_date: null,
    ...over,
  };
}

test("groups compulsory subjects before the chosen optional", () => {
  const tree = buildTree([
    topic({ topic_id: "a", subject_id: "s2", subject: "PSIR Paper-1",
            selection_kind: "elective" }),
    topic({ topic_id: "b" }),
  ]);

  expect(tree.map((g) => g.kind)).toEqual(["compulsory", "elective"]);
  expect(tree[0].subjects[0].name).toBe("Quantitative Aptitude");
  expect(tree[1].label).toBe("Your optional");
});

test("a group with no subjects is omitted entirely", () => {
  const tree = buildTree([topic({})]);
  expect(tree).toHaveLength(1);
  expect(tree[0].kind).toBe("compulsory");
});

test("counts roll up to the subject and to each macro topic", () => {
  const tree = buildTree([
    topic({ topic_id: "a" }),
    topic({ topic_id: "b" }),
    topic({ topic_id: "c", parent_topic_id: "m2", parent_topic: "Data" }),
  ]);

  const subject = tree[0].subjects[0];
  expect(subject.count).toBe(3);
  expect(subject.macros.map((m) => [m.name, m.count])).toEqual([
    ["Quantitative methods", 2],
    ["Data", 1],
  ]);
});

test("a root topic files under its subject, not under a blank macro node", () => {
  const tree = buildTree([
    topic({ topic_id: "a", parent_topic_id: null, parent_topic: null }),
  ]);

  expect(tree[0].subjects[0].count).toBe(1);
  expect(tree[0].subjects[0].macros).toEqual([]);
});

test("a macro topic whose name could not be resolved is not a tree node", () => {
  // The parent-name read failed or the parent is outside the user's scope.
  const tree = buildTree([topic({ parent_topic: null })]);

  expect(tree[0].subjects[0].macros).toEqual([]);
  // ...but the topic is still counted and still reachable from the subject.
  expect(tree[0].subjects[0].count).toBe(1);
  expect(
    topicsForNode([topic({ parent_topic: null })], {
      subjectId: "s1",
      macroId: null,
    }),
  ).toHaveLength(1);
});

test("selecting a subject shows every topic in it, macro children included", () => {
  const items = [
    topic({ topic_id: "a" }),
    topic({ topic_id: "b", parent_topic_id: "m2", parent_topic: "Data" }),
  ];

  expect(topicsForNode(items, { subjectId: "s1", macroId: null })).toHaveLength(2);
  expect(topicsForNode(items, { subjectId: "s1", macroId: "m2" })).toHaveLength(1);
});

test("topics with no parent are reachable under the subject node", () => {
  const items = [topic({ topic_id: "a", parent_topic_id: null })];
  expect(topicsForNode(items, { subjectId: "s1", macroId: null })).toHaveLength(1);
  expect(topicsForNode(items, { subjectId: "s1", macroId: UNGROUPED })).toHaveLength(1);
});

test("search matches topic names anywhere in the syllabus, case-insensitively", () => {
  const items = [
    topic({ topic_id: "a", topic: "Balance of power" }),
    topic({ topic_id: "b", topic: "Percentage", subject_id: "s2",
            subject: "PSIR", selection_kind: "elective" }),
  ];

  expect(searchTopics(items, "percent").map((i) => i.topic_id)).toEqual(["b"]);
  expect(searchTopics(items, "POWER").map((i) => i.topic_id)).toEqual(["a"]);
});

test("search does not match on subject name", () => {
  // "history" would otherwise return every topic in the History paper.
  const items = [topic({ topic_id: "a", subject: "History Paper-1", topic: "Mauryan state" })];
  expect(searchTopics(items, "history")).toEqual([]);
});

test("an empty query matches nothing rather than everything", () => {
  expect(searchTopics([topic({})], "   ")).toEqual([]);
});

test("firstNode picks the first subject of the first group", () => {
  const tree = buildTree([
    topic({ topic_id: "a", subject_id: "s2", subject: "PSIR",
            selection_kind: "elective" }),
    topic({ topic_id: "b" }),
  ]);
  expect(firstNode(tree)).toEqual({ subjectId: "s1", macroId: null });
  expect(firstNode([])).toBeNull();
});

test("sameNode compares both halves", () => {
  expect(sameNode({ subjectId: "s1", macroId: null }, { subjectId: "s1", macroId: null })).toBe(true);
  expect(sameNode({ subjectId: "s1", macroId: "m1" }, { subjectId: "s1", macroId: null })).toBe(false);
  expect(sameNode(null, null)).toBe(false);
});

test("positionOf names subject and macro topic, skipping what is absent", () => {
  expect(positionOf(topic({}))).toBe("Quantitative Aptitude › Quantitative methods");
  expect(positionOf(topic({ parent_topic: null }))).toBe("Quantitative Aptitude");
});
