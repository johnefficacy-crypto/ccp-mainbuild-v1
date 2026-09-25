"""Shared builder for REG-CORPUS authored questions (SEBI/PFRDA/IFSCA).
Same schema as the Costing pilot. Every builder script does:

    from reglib import Batch, inr, R, pct, lakh
    B = Batch("REG-CORPUS-FIN-A", subject="finance", prefix="FIN")
    B.add(micro="fin-...-slug", level="L3", stem=..., correct=..., wrongs=[(text, error), x3],
          steps=[...], formula="...", trap="...", kind="numerical"|"conceptual"|"statement"|"case",
          group=None, verify_fact=False, ref="pattern note / statutory ref")
    B.write()   # validates + balances keys + writes out/<batch>.json and out/<batch>_review.md
"""
import json, random, os, csv
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
LEVEL_DIFF = {"L1": "easy", "L2": "medium", "L3": "hard", "L4": "hard"}


def inr(n, dec=0):
    neg = n < 0
    n = abs(n)
    if dec:
        whole, frac = f"{n:.{dec}f}".split(".")
    else:
        whole, frac = str(int(round(n))), None
    if len(whole) > 3:
        last3, rest = whole[-3:], whole[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:]); rest = rest[:-2]
        if rest: groups.insert(0, rest)
        whole = ",".join(groups + [last3])
    s = whole + (f".{frac}" if frac else "")
    return ("-" if neg else "") + s


def R(n, dec=0): return f"₹{inr(n, dec)}"
def pct(x, d=2): return f"{x*100:.{d}f}%".replace(".00%", "%")
def lakh(x, d=2): return f"₹{x/1e5:,.{d}f} lakh"
def crore(x, d=2): return f"₹{x/1e7:,.{d}f} crore"


def load_catalogue(subject):
    rows = {}
    with open(os.path.join(HERE, "lists", f"{subject}.tsv"), encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            rows[r["slug"]] = {"name": r["name"], "exams": [e for e in r["exams"].split(",") if e]}
    return rows


class Batch:
    def __init__(self, batch, subject, prefix):
        self.batch, self.subject, self.prefix = batch, subject, prefix
        self.cat = load_catalogue(subject)
        self.Q = []

    def add(self, micro, level, stem, correct, wrongs, steps, formula, trap,
            kind="numerical", group=None, verify_fact=False, ref=None):
        qid = f"{self.prefix}-{len(self.Q)+1:03d}"
        assert micro in self.cat, f"{qid}: unknown microtopic slug {micro}"
        assert level in LEVEL_DIFF, qid
        assert len(wrongs) == 3, f"{qid}: need exactly 3 wrong options"
        texts = [str(correct)] + [str(w[0]) for w in wrongs]
        assert len(set(texts)) == 4, f"{qid}: duplicate option {texts}"
        assert all(t.strip() for t in texts), f"{qid}: empty option"
        assert steps and formula is not None and trap, f"{qid}: explanation incomplete"
        self.Q.append({
            "id": qid, "subject": self.subject,
            "microtopic_slug": micro, "microtopic_name": self.cat[micro]["name"],
            "exams": self.cat[micro]["exams"],
            "rubric_level": level, "difficulty": LEVEL_DIFF[level],
            "question_kind": kind, "stimulus_group": group, "stem": stem,
            "_correct": str(correct), "_wrongs": [(str(t), e) for t, e in wrongs],
            "explanation": {"steps": steps, "formula_used": formula, "trap": trap},
            "source_kind": "authored", "provenance": "ai_drafted", "review_status": "draft",
            "verify_fact": bool(verify_fact),
            "source_refs": [{"type": "pattern_only" if not verify_fact else "statutory_or_standard",
                             "note": ref or "Standard exam pattern (ICAI/ICMAI/standard texts). Original figures and entities; no text reproduced."}],
        })
        return qid

    def _finalise(self):
        n = len(self.Q)
        pos = ([0, 1, 2, 3] * (n // 4 + 1))[:n]
        random.Random(self.batch + "-keys").shuffle(pos)
        for q, p in zip(self.Q, pos):
            wrong = list(q.pop("_wrongs")); random.Random(q["id"]).shuffle(wrong)
            c = q.pop("_correct")
            opts = [{"text": t, "is_correct": False, "error": e} for t, e in wrong]
            opts.insert(p, {"text": c, "is_correct": True, "error": None})
            for i, o in enumerate(opts): o["label"] = "ABCD"[i]
            q["options"] = opts
            q["correct_label"] = "ABCD"[p]

    def write(self):
        self._finalise()
        out = os.path.join(HERE, "out")
        os.makedirs(out, exist_ok=True)
        lv = Counter(q["rubric_level"] for q in self.Q)
        kp = Counter(q["correct_label"] for q in self.Q)
        mt = Counter(q["microtopic_slug"] for q in self.Q)
        json.dump({"batch": self.batch, "subject": self.subject, "count": len(self.Q),
                   "levels": lv, "questions": self.Q},
                  open(os.path.join(out, f"{self.batch}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        md = [f"# {self.batch} — {self.subject} — SME review sheet ({len(self.Q)} Q)\n",
              f"Levels {dict(lv)} · key positions {dict(kp)} · microtopics covered {len(mt)}/{len(self.cat)}",
              "Status `ai_drafted` / `draft`. ⚠ = verify_fact (statute / rate / threshold — check against current official text).\n"]
        for q in self.Q:
            flag = " ⚠" if q["verify_fact"] else ""
            md.append(f"\n---\n\n## {q['id']} · {q['rubric_level']} · {q['difficulty']} · {q['microtopic_name']}{flag}\n")
            md.append(q["stem"] + "\n")
            for o in q["options"]:
                md.append(f"- **{o['label']}.** {o['text']}" + (" ✅" if o["is_correct"] else f"  _(error: {o['error']})_"))
            md.append("\n**Working**\n")
            md += [f"{i+1}. {s}" for i, s in enumerate(q["explanation"]["steps"])]
            md.append(f"\n**Formula:** {q['explanation']['formula_used']}  \n**Trap:** {q['explanation']['trap']}")
            md.append("\n**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:\n")
        open(os.path.join(out, f"{self.batch}_review.md"), "w", encoding="utf-8").write("\n".join(md))
        print(f"{self.batch}: {len(self.Q)} Q · levels {dict(lv)} · keys {dict(kp)} · microtopics {len(mt)}/{len(self.cat)}")
        return self.Q
