"""Tier classification for the Recruitment Verification Gateway.

Pure function. Reads the scraped/extracted payload + the source row and
returns a classification dict:

    {
        "criticality_tier": "A_HIGH_STAKES" | "B_TECHNICAL_CONDITIONAL" | "C_STANDARD_LONG_TAIL",
        "exam_family_key": str | None,
        "review_strategy": str,
        "publish_policy": str,
    }

The classifier is policy-agnostic — it never reads the DB and never
decides "should we publish?". It only assigns a tier and an
exam-family hint. Downstream services translate those into actions.

Tier rules (mirrors the spec):

* **Tier A** — high-stakes / mass-volume. UPSC, SSC, IBPS, SBI, RBI,
  banking-regulator, Railways, Defence, Regulatory, State PSC, major
  state police/teacher/clerical exams.
* **Tier B** — technical / conditional. PSU, university, research
  institutes, local body, GATE-based, posts with domicile / language /
  certificate-heavy conditional rules.
* **Tier C** — long-tail / low-risk standard. Default. Small local
  notices, simple one-post recruitments.

Tie-break: Tier A wins over Tier B; Tier B wins over Tier C. A signal
strong enough to be Tier A (e.g. UPSC) is never demoted by a Tier-B
keyword in the same payload.
"""
from __future__ import annotations

import re
from typing import Any

from .verification_policy import (
    TIER_POLICIES,
    CriticalityTier,
    policy_for_tier,
)


# ── Tier A signals ──────────────────────────────────────────────────────
#
# Exam-family key is exposed so the report row carries a stable identifier
# the admin UI can use to bucket "all UPSC reports" / "all SSC reports".
#
# Each family carries two needle kinds:
#   * PHRASES  — matched as plain substrings. Safe for multi-word org names.
#   * ACRONYMS — matched on non-alphanumeric boundaries (see ``_acronym_re``),
#                so a short token like ``trai`` / ``nhb`` / ``psc`` matches the
#                standalone acronym but NOT the middle of a longer word
#                (``training`` / ``national housing`` / ``campscene``). Raw
#                substring membership on acronyms is the bug class this fixes:
#                the old bare ``tra`` false-matched extra/registration/
#                maharashtra, and ``trai`` alone would still catch training/trainee.
_TIER_A_FAMILIES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("upsc",          ("upsc", "union public service commission"), ()),
    ("ssc",           ("ssc", "staff selection commission"), ()),
    ("ibps",          ("ibps", "institute of banking personnel selection"), ()),
    ("sbi",           ("sbi po", "sbi clerk", "state bank of india"), ()),
    ("rbi",           ("rbi grade", "reserve bank of india"), ()),
    # Financial Regulatory & Development Institutions family (Lane R):
    # development-finance institutions. Full org names as phrases; NHB / EXIM /
    # NaBFID acronyms matched on boundaries.
    ("banking",       (
        "nabard", "sidbi",
        "national housing bank", "export-import bank of india",
        "national bank for financing infrastructure",
    ), ("nhb", "exim", "nabfid")),
    ("railways",      ("rrb", "railway recruitment board", "indian railways"), ()),
    ("defence",       (
        "indian army", "indian navy", "indian air force", "iaf",
        "afcat", "nda recruitment", "cds", "agniveer", "drdo recruitment",
        "coast guard", "bsf", "crpf", "cisf", "itbp", "ssb recruitment",
    ), ()),
    # Financial-sector regulators (Lane R). Full org names as phrases; the
    # SEBI/IRDAI/PFRDA/IFSCA/TRAI acronyms matched on boundaries.
    ("regulatory",    (
        "securities and exchange board of india",
        "insurance regulatory and development authority",
        "pension fund regulatory and development authority",
        "international financial services centres authority",
    ), ("sebi", "irdai", "pfrda", "ifsca", "trai")),
    # "<State> Public Service Commission" — matched by phrase, and by the
    # <letters>PSC acronym shape (MPSC/UPPSC/TNPSC…) via a boundary regex
    # below. UPSC is matched earlier in this tuple, so it is never demoted.
    ("state_psc",     ("public service commission", "state public service commission"), ()),
    ("state_police",  ("state police recruitment", "police constable", "police sub-inspector", "police si"), ()),
    ("state_teacher", ("tet ", "ctet", "teacher eligibility", "teacher recruitment"), ()),
    ("state_clerical", ("junior assistant recruitment", "clerk recruitment"), ()),
)


def _acronym_re(tokens: tuple[str, ...]) -> re.Pattern[str] | None:
    """Compile an alternation that matches any token on non-alphanumeric
    boundaries — the fix for short acronyms false-matching inside words."""
    if not tokens:
        return None
    alts = "|".join(re.escape(t) for t in tokens)
    return re.compile(r"(?<![a-z0-9])(?:" + alts + r")(?![a-z0-9])")


# Precompiled per-family acronym matchers (boundary-aware).
_TIER_A_ACRONYM_RE: dict[str, re.Pattern[str]] = {
    key: rx
    for key, _phrases, acronyms in _TIER_A_FAMILIES
    if (rx := _acronym_re(acronyms)) is not None
}
# State-PSC acronyms follow the <letters>PSC shape: PSC, MPSC, UPPSC, TNPSC,
# WBPSC, APPSC… "upsc" also fits, but the upsc family is matched earlier.
_TIER_A_ACRONYM_RE["state_psc"] = re.compile(r"(?<![a-z0-9])[a-z]{0,4}psc(?![a-z0-9])")


# ── Tier B signals ──────────────────────────────────────────────────────
_TIER_B_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("psu",         ("psu recruitment", "ongc", "iocl", "bpcl", "hpcl", "ntpc", "bhel", "gail", "powergrid", "sail")),
    ("university",  ("university recruitment", "professor recruitment", "assistant professor", "non-teaching")),
    ("research",    ("isro", "drdo scientist", "csir", "barc", "iisc", "tifr")),
    ("local_body",  ("municipal corporation", "panchayat", "zilla parishad", "nagar nigam")),
    ("gate_based",  ("gate score", "through gate", "gate-based")),
)


# Conditional-rule keywords that nudge an unclassified payload into Tier B
# even when no family keyword matches. Domicile/language/certificate-heavy
# posts are the spec's canonical Tier B examples.
_TIER_B_CONDITIONAL_HINTS: tuple[str, ...] = (
    "domicile", "local language", "vernacular", "experience required",
    "first class", "discipline-specific", "professional certificate",
    "license required", "gate ",
)


_GOVT_HOST_HINTS = (".gov.in", ".nic.in")


def _gather_text(extracted: dict[str, Any], queue_item: dict[str, Any] | None) -> str:
    parts: list[str] = []
    for k in ("title", "name", "organization_name", "source_name", "notification_number"):
        v = extracted.get(k)
        if isinstance(v, str):
            parts.append(v)
    posts = extracted.get("posts")
    if isinstance(posts, list):
        for p in posts:
            if not isinstance(p, dict):
                continue
            for k in ("post_name", "education_required", "raw_requirement_text"):
                v = p.get(k)
                if isinstance(v, str):
                    parts.append(v)
            for k in ("language_requirements", "disciplines"):
                v = p.get(k)
                if isinstance(v, list):
                    parts.extend(str(x) for x in v if isinstance(x, (str, int, float)))
    if queue_item:
        for k in ("source_url", "source_name"):
            v = queue_item.get(k)
            if isinstance(v, str):
                parts.append(v)
    return " ".join(parts).lower()


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(n in haystack for n in needles)


def _match_family(haystack: str, families: tuple[tuple[str, tuple[str, ...]], ...]) -> str | None:
    for key, needles in families:
        if _has_any(haystack, needles):
            return key
    return None


def _match_tier_a(haystack: str) -> str | None:
    """Tier-A family match: substring phrases OR boundary-aware acronyms,
    scanned in priority order (UPSC before generic state PSC, etc.)."""
    for key, phrases, _acronyms in _TIER_A_FAMILIES:
        if phrases and _has_any(haystack, phrases):
            return key
        rx = _TIER_A_ACRONYM_RE.get(key)
        if rx is not None and rx.search(haystack):
            return key
    return None


def classify_recruitment(
    extracted_data: dict[str, Any] | None = None,
    queue_item: dict[str, Any] | None = None,
    *,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a scraped recruitment payload into a tier + exam family.

    Args:
      extracted_data: The ``scrape_queue.extracted_data`` blob.
      queue_item: Optional surrounding queue row (for source_url / name).
      source: Optional ``source_registry`` row. ``org_type`` and
              ``trust_tier`` are used as weak hints; the family-keyword
              table is the dominant signal.
    """
    extracted = extracted_data or {}
    text = _gather_text(extracted, queue_item)

    # ── 1. Tier A — strongest signal. Win first, never demoted. ─────────
    a_family = _match_tier_a(text)
    if a_family:
        return _bundle("A_HIGH_STAKES", a_family)

    # ── 2. Source-registry hint can still pull us into Tier A when the
    #       payload text is sparse (e.g. an SSC source whose extracted
    #       title got truncated to "Notification 2026").
    if source:
        org_type = (source.get("org_type") or "").lower() if isinstance(source, dict) else ""
        if org_type in {"upsc", "ssc"}:
            return _bundle("A_HIGH_STAKES", org_type)
        if org_type in {"banking", "railway", "defence"}:
            family = {"banking": "banking", "railway": "railways", "defence": "defence"}[org_type]
            return _bundle("A_HIGH_STAKES", family)

    # ── 3. Tier B — explicit family match, then conditional-rule hints. ─
    b_family = _match_family(text, _TIER_B_FAMILIES)
    if b_family:
        return _bundle("B_TECHNICAL_CONDITIONAL", b_family)

    if _has_any(text, _TIER_B_CONDITIONAL_HINTS):
        return _bundle("B_TECHNICAL_CONDITIONAL", "conditional_rules")

    # ── 4. Default — Tier C. ───────────────────────────────────────────
    return _bundle("C_STANDARD_LONG_TAIL", None)


def _bundle(tier: CriticalityTier, exam_family_key: str | None) -> dict[str, Any]:
    policy = policy_for_tier(tier)
    return {
        "criticality_tier": tier,
        "exam_family_key": exam_family_key,
        "review_strategy": policy["review_strategy"],
        "publish_policy": policy["publish_policy"],
    }


__all__ = ["classify_recruitment", "TIER_POLICIES"]
