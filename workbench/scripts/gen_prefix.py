import csv, hashlib, re
rows = []
for enc in ("utf-8","cp1252"):
    try:
        rows = list(csv.DictReader(open("workbench/catalogs/mains-rename-proposal-v2.csv", encoding=enc)))
        break
    except UnicodeDecodeError:
        continue
P = {"General Studies I":"gs1","General Studies II":"gs2","General Studies III":"gs3","General Studies IV":"gs4"}
tgt = [r for r in rows if r["proposed_name"].startswith("Recent developments:")]
print(len(tgt), "rows to prefix")
def q(s): return "'" + s.replace("'","''") + "'"
def slug(p,n):
    k = re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-")[:80]
    return p + "-" + k + "-" + hashlib.md5(n.encode()).hexdigest()[:8]
vals = ",\n".join("  (%s::uuid, %s, %s)" % (q(r["id"]), q(r["proposed_name"]), q(slug(P[r["subject"]], r["proposed_name"]))) for r in tgt)
sql = "BEGIN;\n\nUPDATE public.topics t SET name = v.name, slug = v.slug\nFROM (VALUES\n" + vals + "\n) AS v(id, name, slug)\nWHERE t.id = v.id;\n\nDO $$\nDECLARE n int;\nBEGIN\n  SELECT count(*) INTO n FROM public.topics WHERE name LIKE 'Recent developments:%';\n  IF n <> " + str(len(tgt)) + " THEN RAISE EXCEPTION 'expected " + str(len(tgt)) + " prefixed rows, got %', n; END IF;\nEND $$;\n\nCOMMIT;\n"
open("mains_recent_prefix.sql","w",encoding="utf-8").write(sql)
print("wrote mains_recent_prefix.sql")

