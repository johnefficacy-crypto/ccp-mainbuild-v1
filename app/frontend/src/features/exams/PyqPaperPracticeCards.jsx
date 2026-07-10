import React from "react";

// Paper-level practice cards — the DEFAULT primary section of the PYQ hub, so a
// 10-paper exam shows 10 cards instead of 1,000 question cards. Driven by
// pyq-summary `papers[]`. `practice_ready_count` / `practice_enabled` come from
// the launch-accurate backend predicate, so a card only offers "Practice paper"
// when the launcher will actually assemble a pool.

function PaperCard({ paper, onPractice, practicing, practiceDisabled }) {
  const qCount = paper.question_count || 0;
  const ready = paper.practice_ready_count || 0;
  const enabled = Boolean(paper.practice_enabled);
  return (
    <div className="rounded-xl border border-clay-100 bg-white p-4 flex flex-col gap-2" data-testid="pyq-paper-card">
      <div className="flex flex-wrap items-center gap-1.5">
        {paper.year ? <span className="pill pill-clay text-[11px]">{paper.year}</span> : null}
        {paper.phase_name ? <span className="pill pill-dusk text-[11px]">{paper.phase_name}</span> : null}
        {paper.subject_name ? <span className="pill pill-sage text-[11px]">{paper.subject_name}</span> : null}
      </div>
      <div className="text-sm text-muted-foreground">
        {qCount.toLocaleString("en-IN")} question{qCount === 1 ? "" : "s"} ·{" "}
        <span className={ready > 0 ? "text-sage-700 font-medium" : ""}>
          {ready.toLocaleString("en-IN")} practice-ready
        </span>
      </div>
      <div className="mt-auto pt-1">
        {enabled ? (
          <button
            type="button"
            onClick={() => onPractice(paper.paper_id)}
            disabled={practiceDisabled}
            className="btn btn-primary text-xs disabled:opacity-40"
            data-testid="pyq-paper-practice-btn"
          >
            {practicing ? "Starting…" : "Practice paper"}
          </button>
        ) : (
          <span className="text-[11px] text-muted-foreground" data-testid="pyq-paper-not-ready">
            Not available for practice yet
          </span>
        )}
      </div>
    </div>
  );
}

export default function PyqPaperPracticeCards({ papers, onPractice, practicingPaperId, practiceDisabled, sr }) {
  if (!papers || papers.length === 0) {
    return (
      <div
        className="rounded-2xl border border-dashed border-clay-200 bg-clay-50/50 p-6 text-center text-sm text-muted-foreground"
        data-testid="pyq-paper-cards-empty"
      >
        No verified papers to practice yet — check back as more are verified.
      </div>
    );
  }
  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="pyq-paper-cards">
      {papers.map((p) => (
        <PaperCard
          key={p.paper_id}
          paper={p}
          onPractice={onPractice}
          practicing={sr && practicingPaperId === p.paper_id}
          practiceDisabled={practiceDisabled}
        />
      ))}
    </div>
  );
}
