import sys
sys.path.insert(0, 'app/backend')
from app.exam_intelligence.option_normalize import option_hash

rows = [
    ("6ae8886a-0492-44e4-a03e-1dc31655065d", "1 only"),
    ("7660a907-2a85-41a4-b506-5f70f69fb14e", "2 only"),
    ("dfb1705d-ef33-44e8-a242-c90eacaacae9", "Both 1 and 2"),
    ("7f508f15-13c6-4200-9012-a82500ea18b5", "Neither 1 nor 2"),
    ("7172a39a-a10d-47a4-bb21-54ac5d0cb634", "1, 2 and 3"),
    ("91085a32-72aa-484a-986e-e96dc0c1e536", "The money which is tendered in courts of law to defray the fee of legal cases"),
    ("d9261a3f-3077-46ae-bf6f-e9d74c79f71c", "The money which a creditor is under compulsion to accept in settlement of his claims"),
    ("a75247ed-0ade-4d6f-8f5c-68dfbdd3fc65", "The bank money in the form of cheques, drafts, bills of exchange, etc."),
    ("94e3252f-d6eb-47da-86bf-8f3e18b9b5e6", "The metallic money in circulation in a country"),
    ("17589fde-7cb5-407d-a04a-ba7b8791cac7", "1 only"),
    ("1ca4f777-5891-4c07-a4a9-51bc34a3df72", "2 and 3 only"),
    ("5e237b73-f194-44d9-b1c8-a1dd9c8b5a7a", "1 and 3 only"),
    ("ebb2e5b2-da48-49fc-85a6-0e65ede87976", "1, 2 and 3"),
]

lines = ["UPDATE public.pyq_options AS o",
         "SET normalized_option_hash = v.h",
         "FROM (VALUES"]
vals = [f"  ('{oid}'::uuid, '{option_hash(t)}')" for oid, t in rows]
lines.append(",\n".join(vals))
lines.append(") AS v(id, h)")
lines.append("WHERE o.id = v.id AND o.normalized_option_hash IS NULL;")
open("hash_fix.sql", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
