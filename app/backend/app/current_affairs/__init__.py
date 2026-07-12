"""Current-Affairs pipeline (GA lane).

GQR-G2 delivers the source + evidence authority layer only: a source registry
that is deliberately SEPARATE from ``source_registry`` (which the recruitment
runner consumes), immutable document snapshots, and the event/claim/evidence
graph. Ingestion reuses ``app.scraping.fetcher`` for conditional fetch.

No LLM, no learner UI, and no scheduler wiring live here — those land in later
GQR-G* PRs (see docs/architecture/current-affairs-pipeline.md).
"""
