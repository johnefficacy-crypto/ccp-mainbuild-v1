import json, io, os, collections
SRC = r"workbench/exports/optionals/questions_export.json"
OUT = r"workbench/exports/optionals"
PREFIX = {
    "PSIR-P1": "psir_p1",   "PSIR-P2": "psir_p2",
    "PUBAD-P1": "pubad_p1", "PUBAD-P2": "pubad_p2",
    "SOCIO-P1": "socio_p1", "SOCIO-P2": "socio_p2",
    "ANTH-P1": "anth_p1",   "ANTH-P2": "anth_p2",
    "HIST-P1": "hist_p1",   "HIST-P2": "hist_p2",
    "GEOG-P1": "geog_p1",   "GEOG-P2": "geog_p2",
}
d = json.load(io.open(SRC, encoding="utf-8"))
rows = d["items"] if isinstance(d, dict) and "items" in d else d
buckets = collections.defaultdict(list)
unmatched = []
for q in rows:
    ref = q.get("source_question_ref") or ""
    for pfx, stem in PREFIX.items():
        if ref.startswith(pfx + "-"):
            buckets[stem].append(q); break
    else:
        unmatched.append(ref)
for stem, qs in sorted(buckets.items()):
    p = os.path.join(OUT, "questions_%s.json" % stem)
    json.dump(qs, io.open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%-10s %5d -> %s" % (stem, len(qs), p))
print("total split", sum(len(v) for v in buckets.values()))
print("unmatched  ", len(unmatched), unmatched[:5])
