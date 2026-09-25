"""Shared helpers for REG-CORPUS-CA-A part modules (caa_p1..caa_p4)."""
import os as _os; _REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, _REG)
from reglib import inr, R, pct, lakh, crore  # noqa: F401
from datetime import date, timedelta  # noqa: F401
import calendar

S = {
    "adj": "cos-adjournment-when-quorum-is-absent-efcc1098",
    "age": "cos-age-limits-for-directors-afb4a3c2",
    "alt": "cos-alternate-director-b721cc85",
    "sc": "cos-appeal-to-the-supreme-court-989ea1bf",
    "nclat_appeal": "cos-appeal-window-to-the-nclat-3546149a",
    "consult": "cos-appointment-consultation-process-ba864eaa",
    "valuer": "cos-appointment-of-a-registered-valuer-ecf180fe",
    "din": "cos-appointment-din-and-intimation-to-the-registrar-020c8577",
    "rotation": "cos-appointment-rotation-and-tenure-of-auditors-d3cef3ad",
    "ac": "cos-audit-committee-composition-and-role-a4e5f01c",
    "bo": "cos-beneficial-owner-when-a-third-person-qualifies-90e3acff",
    "boardcomp": "cos-board-composition-minimum-and-maximum-directors-81ee33dd",
    "bmfreq": "cos-board-meetings-frequency-and-first-meeting-timing-612ad98e",
    "bonus": "cos-bonus-shares-conditions-81a5d883",
    "buyback": "cos-buy-back-of-securities-s-68-conditions-and-limits-78870170",
    "cag": "cos-cag-appointment-of-auditors-and-the-appointment-window-a18b0420",
    "casual": "cos-casual-vacancy-in-the-office-of-auditor-a68d141c",
    "crc": "cos-central-registration-centre-and-certificate-of-incorporation-952d214d",
    "nclat": "cos-constitution-and-powers-of-the-nclat-7d3f5096",
    "cost": "cos-cost-audit-e84ebed0",
    "delivery": "cos-delivery-timeline-for-transfer-of-securities-9e7bf1bf",
    "dep5": "cos-deposit-in-a-scheduled-bank-within-five-days-a03d922d",
    "disq": "cos-disqualifications-for-appointment-as-director-f45b8a22",
    "divprof": "cos-divisible-profits-and-managerial-remuneration-3e7deff3",
    "duties": "cos-duties-of-directors-066c0810",
    "esop": "cos-esop-and-sweat-equity-s-54-lock-in-ce77fa51",
    "firm": "cos-eligibility-of-a-firm-as-auditor-98009b64",
    "sch3": "cos-format-of-financial-statements-governed-by-schedule-iii-5a5a1914",
    "rights": "cos-further-issue-of-capital-and-rights-issue-6997c3f1",
    "iepf": "cos-iepf-permitted-and-prohibited-uses-238257fd",
    "idelig": "cos-independent-director-eligibility-and-exclusions-44e8bff4",
    "idtenure": "cos-independent-directors-criteria-and-tenure-4a63ab88",
    "interim": "cos-interim-dividend-permitted-sources-29ad1710",
    "discount": "cos-issue-of-shares-at-a-discount-exceptions-6e4d64ca",
    "kinds": "cos-kinds-of-share-capital-f0d25eb8",
    "loans": "cos-loans-to-directors-f33d3460",
    "maxgap": "cos-maximum-gap-between-consecutive-board-meetings-a0608bc2",
    "maxdir": "cos-maximum-number-of-directorships-c4a0d44e",
    "prospectus": "cos-misstatement-in-prospectus-civil-and-criminal-liability-a76a4447",
    "nclatage": "cos-nclat-chairperson-age-limit-ef26c89a",
    "nrc": "cos-nomination-and-remuneration-committee-a611f525",
    "noticebm": "cos-notice-period-for-a-board-meeting-dccb5a18",
    "vc": "cos-participation-by-video-conferencing-111c3385",
    "div30": "cos-payment-of-dividend-within-thirty-days-22df5de4",
    "powers": "cos-powers-exercisable-only-at-a-board-meeting-190320e6",
    "auditrep": "cos-powers-duties-and-the-auditor-s-report-ed39c15d",
}

AR = ["Both A and R are true, and R is the correct explanation of A",
      "Both A and R are true, but R is not the correct explanation of A",
      "A is true, but R is false",
      "A is false, but R is true"]


def ar(ci, labels):
    """ci = index of correct A-R option; labels = dict idx->error label for the other three."""
    return AR[ci], [(AR[i], labels[i]) for i in range(4) if i != ci]


def D(d):
    return f"{d.day} {calendar.month_name[d.month]} {d.year}"


def add_months(d, m):
    y, mo = divmod(d.month - 1 + m, 12)
    y += d.year
    mo += 1
    return date(y, mo, min(d.day, calendar.monthrange(y, mo)[1]))


def L(x, dec=0):
    return f"₹{inr(x, dec)} lakh"


def Cr(x, dec=2):
    """x already in crore"""
    return f"₹{x:,.{dec}f} crore"


def q(B, key, level, stem, correct, wrongs, steps, formula, trap, kind="conceptual", group=None, ref=None):
    from caa_overrides import OVR
    correct = OVR.get(correct, correct)
    wrongs = [(OVR.get(t, t), e) for t, e in wrongs]
    return B.add(micro=S[key], level=level, stem=stem, correct=correct, wrongs=wrongs, steps=steps,
                 formula=formula, trap=trap, kind=kind, group=group,
                 verify_fact=ref is not None, ref=ref)
