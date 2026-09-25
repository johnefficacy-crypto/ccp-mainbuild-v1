"""Shared helpers for REG-CORPUS-CA-B part modules (companies-act, list B)."""
import sys
sys.path.insert(0, '/home/claude/corpus')
from datetime import date, timedelta
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401

M = {
    "pref": "cos-preference-shares-issue-redemption-and-maximum-tenure-a36ad927",
    "pp": "cos-private-placement-procedure-and-limits-6dfbad90",
    "prosp": "cos-prospectus-matters-to-be-stated-32a01360",
    "s23": "cos-public-offer-private-placement-and-rights-or-bonus-issue-56111832",
    "demat": "cos-public-offers-to-be-in-dematerialised-form-39dc6b59",
    "s127": "cos-punishment-for-failure-to-distribute-dividend-370783bd",
    "bq": "cos-quorum-for-a-board-meeting-eaaed9ee",
    "gq": "cos-quorum-requirements-for-a-general-meeting-f1ef188d",
    "red": "cos-reduction-of-share-capital-dfd7d905",
    "chg": "cos-registration-of-charges-73e3ea5e",
    "rpt": "cos-related-party-transactions-68181697",
    "remcg": "cos-removal-by-special-resolution-with-central-government-approv-d019da30",
    "strike": "cos-removal-of-name-from-the-register-of-companies-02ef9f3b",
    "fraud": "cos-reporting-of-fraud-by-the-auditor-747e37c1",
    "resig": "cos-resignation-and-intimation-of-resignation-d30efe66",
    "circ": "cos-resolutions-passed-by-circulation-61c1b2bb",
    "sched": "cos-schedules-of-the-companies-act-2013-5eddaf0e",
    "svc": "cos-services-an-auditor-may-render-c7012cb4",
    "shelf": "cos-shelf-prospectus-and-abridged-prospectus-e6df180d",
    "ssd": "cos-small-shareholders-director-6ce7c901",
    "spaud": "cos-special-auditor-who-appoints-ab384079",
    "src": "cos-stakeholders-relationship-committee-964ed50d",
    "xfer": "cos-transfer-and-transmission-partly-paid-shares-3ad10f34",
    "uda": "cos-transfer-to-the-unpaid-dividend-account-076df915",
    "rect": "cos-tribunal-s-power-to-rectify-its-own-order-424b3b8c",
    "tribrem": "cos-tribunal-ordered-removal-of-an-auditor-9d6be110",
    "opc": "cos-types-of-companies-one-person-company-ace862e4",
    "vac": "cos-vacation-of-office-resignation-and-removal-d74dfbe4",
    "llp": "cos-who-may-sign-for-an-llp-1f241269",
    "wd": "cos-woman-director-and-resident-director-1a248713",
    "s123": "cos-s-123-sources-of-dividend-ac8b492e",
    "s124": "cos-s-124-seven-year-transfer-to-the-iepf-abca0f11",
    "s125": "cos-s-125-constitution-of-the-iepf-ef99b222",
    "csr": "cos-s-135-csr-obligation-and-excess-set-off-727f6a06",
    "s141": "cos-s-141-eligibility-and-disqualification-d8425679",
    "s144": "cos-s-144-prohibited-non-audit-services-59190ee1",
    "s186": "cos-s-186-loans-and-investments-by-a-company-451c33a6",
    "rhp": "cos-s-32-red-herring-prospectus-and-filing-window-5e4b0142",
    "s39": "cos-s-39-minimum-application-money-7fd524e1",
    "s408": "cos-s-408-constitution-of-the-nclt-bb987696",
    "s409": "cos-s-409-qualification-of-president-and-members-3f689af9",
    "s44": "cos-s-44-shares-and-debentures-as-movable-property-0ae16328",
    "s46": "cos-s-46-duplicate-share-certificate-and-penalty-3d5946a0",
    "s52": "cos-s-52-securities-premium-permitted-applications-e2c9f050",
    "s71": "cos-s-71-debentures-and-debenture-trustee-aa8bacb1",
}


def d(y, m, dd):
    return date(y, m, dd)


def ds(x):
    """12 March 2026 style"""
    return f"{x.day} {x.strftime('%B %Y')}"


def plus(x, n):
    return x + timedelta(days=n)


def cr(x, dec=2):
    """x in rupees -> '₹x.xx crore'"""
    return f"₹{x/1e7:,.{dec}f} crore"


def lk(x, dec=2):
    return f"₹{x/1e5:,.{dec}f} lakh"


def stmts(intro, items, ask="Which of the statements given above is/are correct?"):
    body = "\n".join(f"{i+1}. {s}" for i, s in enumerate(items))
    return f"{intro}\n\n{body}\n\n{ask}"


def table(headers, rows, align=None):
    align = align or ["---"] * len(headers)
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(align) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def interest(p, rate, days):
    return p * rate * days / 365
