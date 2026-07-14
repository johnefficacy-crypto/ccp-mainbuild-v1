"""Exam-level baseline and cycle eligibility.

Surface:
  * :func:`evaluator.evaluate_exam_for_user` — pure per-exam decision.
  * :func:`evaluator.evaluate_cycle_eligibility` — cutoff-aware, cycle-scoped
    decision (age measured on the notification's official cut-off date), kept
    separate from the baseline verdict (Lane R §4).
  * :func:`evaluator.summarize_user_eligibility` — group every active exam
    with at least one verified rule by status: eligible / conditional /
    not_eligible / unknown, each carrying an additive per-stream breakdown and
    a cutoff-aware ``cycle`` provenance band.
"""

# Package-level installation is intentional: existing callers import directly
# from ``app.exam_eligibility.evaluator``. Installing before that import returns
# preserves the public surface while applying the cycle-only fail-closed guards.
from . import evaluator as evaluator
from .cycle_runtime_guards import install_cycle_runtime_guards

install_cycle_runtime_guards(evaluator)

__all__ = ["evaluator"]
