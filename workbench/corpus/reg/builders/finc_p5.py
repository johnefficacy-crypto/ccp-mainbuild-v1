"""FIN-C part 5: Income-tax Act, 2025 (w.e.f. 1 April 2026) — 5 questions.
Only structural facts used: replaces the 1961 Act from 1 April 2026; single 'tax year' replaces
'previous year' / 'assessment year'; simplification framing, rates largely unchanged.
No section numbers cited. All computational rates are supplied in the stem as data."""
from finc_common import M, table, statements, stmt_opts, inr, R, pct, TAXREF

PFX = "Under the Income-tax Act, 2025, "


def slab_tax(ti, slabs):
    tax, lo = 0, 0
    for hi, rate in slabs:
        if ti > lo:
            tax += (min(ti, hi) - lo) * rate
        lo = hi
    return tax


def add_all(B):
    ma, md = M("income-tax-assessment"), M("direct-vs-indirect")

    B.add(ma, "L1", PFX + "which concept replaces the twin concepts of 'previous year' and 'assessment year' used under the Income-tax Act, 1961?",
          "A single 'tax year', the year in which the income is earned",
          [("'Financial year' replaces 'previous year'; 'assessment year' continues", "assumes only one of the two terms is renamed"),
           ("An 'accounting year' that follows each assessee's own books of account", "invents an assessee-specific year"),
           ("'Assessment year' alone, with the income of that same year taxed in it", "retains the old term instead of the new 'tax year'")],
          ["The 1961 Act taxed income of the previous year in the following assessment year.",
           "The 2025 Act, in force from 1 April 2026, uses a single 'tax year' — the income and the year of reference are the same."],
          "Old: PY → AY (next year);  New: tax year = year of earning", "The new Act does not keep 'assessment year' as the reference label.",
          kind="conceptual", verify_fact=True, ref=TAXREF)

    B.add(ma, "L2", PFX + "how are the following two periods of Ms Anika's salary income correctly labelled? (i) 1 April 2024 – 31 March 2025, assessed under the Income-tax Act, 1961; (ii) 1 April 2026 – 31 March 2027, taxed under the Income-tax Act, 2025.",
          "(i) Assessment year 2025-26; (ii) tax year 2026-27",
          [("(i) Assessment year 2024-25; (ii) tax year 2026-27", "old-Act income labelled by the year of earning rather than the following AY"),
           ("(i) Assessment year 2025-26; (ii) tax year 2027-28", "AY-style one-year lag carried into the new 'tax year'"),
           ("(i) Previous year 2025-26; (ii) tax year 2027-28", "both periods shifted forward by a year")],
          ["Under the 1961 Act, income of PY 2024-25 (FY 2024-25) is assessed in AY 2025-26.",
           "Under the 2025 Act, income earned in FY 2026-27 is income of tax year 2026-27 — no lag."],
          "FY of earning = tax year (2025 Act);  AY = FY + 1 (1961 Act)", "The one-year lag disappears under the new Act.",
          kind="conceptual", verify_fact=True, ref=TAXREF)

    st = ["Income tax under the new Act remains a direct tax, as its impact and incidence fall on the same person.",
          "The Goods and Services Tax has been merged into the Income-tax Act, 2025 as part of the simplification.",
          "The Income-tax Act, 2025 replaces the Income-tax Act, 1961 with effect from 1 April 2026."]
    c, w = stmt_opts([True, False, True],
                     ["income tax is not shifted to another person", "GST is a separate indirect tax under the GST laws",
                      "the new Act applies from 1 April 2026"])
    B.add(md, "L1", PFX + "consider the following statements:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w,
          ["Income tax is a direct tax: the person on whom it is imposed bears it.",
           "GST remains a separate indirect tax levied under the CGST/SGST/IGST laws; the 2025 Act deals only with income tax.",
           "The 2025 Act replaced the 1961 Act from 1 April 2026."],
          "Direct tax: impact = incidence", "Simplification of the income-tax law did not absorb indirect taxes.",
          kind="statement", verify_fact=True, ref=TAXREF)

    slabs = [(400000, 0), (800000, 0.05), (1200000, 0.10), (1600000, 0.15), (2000000, 0.20), (2400000, 0.25), (10 ** 12, 0.30)]
    sd, reb_lim, reb_max, cess = 75000, 1200000, 60000, 0.04
    stab = table(["Total income (₹)", "Rate"], [["Up to 4,00,000", "Nil"], ["4,00,001 – 8,00,000", "5%"], ["8,00,001 – 12,00,000", "10%"],
                                              ["12,00,001 – 16,00,000", "15%"], ["16,00,001 – 20,00,000", "20%"], ["20,00,001 – 24,00,000", "25%"], ["Above 24,00,000", "30%"]])
    data = (f"Assume the following new-regime slabs apply for tax year 2026-27:\n\n{stab}\n\n"
            f"Assume also: standard deduction from salary ₹{inr(sd)}; rebate equal to the tax (maximum ₹{inr(reb_max)}) where total income does not exceed ₹{inr(reb_lim)}, with no marginal relief; health and education cess 4% on tax.")
    def tax(sal, use_sd=True, rebate=True, cess_on=True, force_rebate=False):
        ti = sal - (sd if use_sd else 0)
        tx = slab_tax(ti, slabs)
        if (rebate and ti <= reb_lim) or force_rebate:
            tx = max(0, tx - min(tx, reb_max))
        return round(tx * (1 + cess) if cess_on else tx)
    sal = 1850000
    t_ok = tax(sal)
    assert t_ok == 161200
    B.add(ma, "L2", PFX + f"compute the tax payable for tax year 2026-27 by Mr Devansh, a resident individual under the new regime whose only income is a salary of ₹{inr(sal)}. {data}",
          R(t_ok),
          [(R(tax(sal, use_sd=False)), "standard deduction not allowed"),
           (R(tax(sal, cess_on=False)), "cess omitted"),
           (R(tax(sal, force_rebate=True)), "rebate allowed although total income exceeds ₹12,00,000")],
          [f"Total income = {inr(sal)} − {inr(sd)} = {inr(sal-sd)}",
           "Tax: 4–8 L @5% = 20,000; 8–12 L @10% = 40,000; 12–16 L @15% = 60,000; 16–17.75 L @20% = 35,000 → 1,55,000",
           f"No rebate (income > 12 L); cess 4% = 6,200 → ₹{inr(t_ok)}"],
          "Tax = Σ slab tax on (Salary − Std deduction) + 4% cess", "Slab rates apply to each band, not to the whole income.",
          verify_fact=True, ref=TAXREF)

    sa, sb = 1260000, 1290000
    ta, tb_ = tax(sa), tax(sb)
    assert ta == 0 and tb_ == 64740
    pair = lambda a, b: f"{'Nil' if a == 0 else R(a)} and {'Nil' if b == 0 else R(b)}"
    opts = [pair(ta, tb_), pair(tax(sa), tax(sb, force_rebate=True)), pair(tax(sa, use_sd=False), tax(sb, use_sd=False)), pair(tax(sa), tax(sb, cess_on=False))]
    assert len(set(opts)) == 4
    B.add(ma, "L3", PFX + f"two resident salaried individuals opt for the new regime for tax year 2026-27: Ms Esha (salary ₹{inr(sa)}) and Mr Farhan (salary ₹{inr(sb)}), with no other income. {data}\n\nTheir tax liabilities respectively are:",
          opts[0],
          [(opts[1], "rebate also given to Farhan although his total income exceeds ₹12,00,000"),
           (opts[2], "standard deduction ignored for both"),
           (opts[3], "cess omitted on Farhan's tax")],
          [f"Esha: total income = {inr(sa-sd)} ≤ 12,00,000 → tax 58,500 fully rebated → Nil",
           f"Farhan: total income = {inr(sb-sd)} > 12,00,000 → tax = 60,000 + 15% × 15,000 = 62,250; no rebate; + 4% cess = ₹{inr(tb_)}"],
          "Rebate only if total income ≤ threshold (as given)", "A ₹30,000 salary difference creates a ₹64,740 tax difference when marginal relief is ignored.",
          verify_fact=True, ref=TAXREF)
