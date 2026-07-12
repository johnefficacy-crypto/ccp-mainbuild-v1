"""Current-affairs LLM generation pipeline (GQR-G3).

Shadow / no-authority: extraction + MCQ generation + independent verification are
LLM-assisted (ADR 0006 — AI is an assistant, not an authority), but every artefact
lands in staging (``current_affairs_question_candidates``) with a deterministic
validation verdict and a full generation audit (``current_affairs_generation_runs``).
Nothing here promotes, publishes, or marks its own output reviewed — promotion into
the objective bank is GQR-G4/G5, behind the operator human gate.

The runtime reuses the EWP LLM-adapter contract (english-writing-practice.md §5):
the LLM call runs with NO DB transaction open; jobs use a lease + fencing token; the
job acknowledgement is atomic with side effects; output is shadow / no authority.
"""
