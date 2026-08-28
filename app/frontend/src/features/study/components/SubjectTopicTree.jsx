import React, { useState } from "react";
import PropTypes from "prop-types";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Pill } from "../../../shared/ui/studyos";

// SubjectTopicTree — aspirant-facing drill-down for ONE subject, backed by
// GET /api/study/subjects/{subject_id}/topics (PR #1032). Renders the macro
// topic → microtopic nesting the endpoint returns and honours its three
// distinct coverage states without ever collapsing them into one another:
//
//   • coverage present (locked)   → priority score + a "high-yield" pill when flagged
//   • coverage === null           → the topic, with NO priority number (a real,
//                                    expected not-yet-scored state, not an error)
//   • is_rollup_zero_evidence      → muted styling + a "not yet reliable" note; never
//                                    shown as real, ranked, evidence-backed guidance
//
// Order is exactly as returned (server sorts priority-desc then name-asc); we
// never re-sort on the client. This is a fresh component (not the dead
// features/study TopicTreePanel, which is flat/multi-subject and assumes the
// old /api/study/topics shape). The admin syllabus-mapper TopicTreePanel is a
// different file entirely and is not touched.

function fmtPriority(score) {
  if (score === null || score === undefined) return null;
  return Math.round(score);
}

function TopicNode({ node, depth }) {
  const children = Array.isArray(node.children) ? node.children : [];
  const hasChildren = children.length > 0;
  const [open, setOpen] = useState(false);

  const rollup = !!node.is_rollup_zero_evidence;
  const coverage = rollup ? null : node.coverage; // a rollup node's score is not real guidance
  const priority = coverage ? fmtPriority(coverage.exam_priority_score) : null;
  const highYield = !!(coverage && coverage.is_high_yield);

  return (
    <li data-testid={`topic-node-${node.topic_id}`}>
      <div
        className={
          "flex items-center gap-2 py-1.5 " +
          (rollup ? "opacity-55" : "")
        }
        style={{ paddingLeft: depth * 16 }}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            aria-label={open ? "Collapse" : "Expand"}
            className="text-slate-500 hover:text-slate-800"
            data-testid={`topic-toggle-${node.topic_id}`}
          >
            {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        ) : (
          <span className="inline-block" style={{ width: 14 }} aria-hidden="true" />
        )}

        <span className={"text-sm " + (rollup ? "text-slate-500" : "text-slate-800")}>
          {node.name || node.topic_id}
        </span>

        {highYield ? (
          <Pill tone="amber" className="text-[10px]">
            high-yield
          </Pill>
        ) : null}

        {rollup ? (
          <span
            className="text-[10.5px] text-slate-400 italic"
            data-testid={`topic-rollup-${node.topic_id}`}
            title="This is a rollup/header node with no verified PYQ evidence yet — not reliable guidance."
          >
            not yet reliable
          </span>
        ) : priority !== null ? (
          <span
            className="num-mono text-[11px] text-slate-500 ml-auto"
            data-testid={`topic-priority-${node.topic_id}`}
          >
            priority {priority}
          </span>
        ) : (
          <span
            className="text-[10.5px] text-slate-400 ml-auto"
            data-testid={`topic-unscored-${node.topic_id}`}
          >
            not yet scored
          </span>
        )}
      </div>

      {hasChildren && open ? (
        <ul data-testid={`topic-children-${node.topic_id}`}>
          {children.map((child) => (
            <TopicNode key={child.topic_id} node={child} depth={depth + 1} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

const NODE_SHAPE = {
  topic_id: PropTypes.string,
  name: PropTypes.string,
  level: PropTypes.string,
  parent_topic_id: PropTypes.string,
  evidence_count: PropTypes.number,
  is_rollup_zero_evidence: PropTypes.bool,
  coverage: PropTypes.shape({
    exam_priority_score: PropTypes.number,
    is_high_yield: PropTypes.bool,
  }),
  children: PropTypes.array,
};

TopicNode.propTypes = {
  node: PropTypes.shape(NODE_SHAPE).isRequired,
  depth: PropTypes.number.isRequired,
};

export default function SubjectTopicTree({ topics, loading, error, onRetry }) {
  if (loading) {
    return (
      <p className="mt-2 text-xs text-slate-500" data-testid="topic-tree-loading" role="status">
        Loading topics…
      </p>
    );
  }
  if (error) {
    return (
      <div className="mt-2 text-xs text-clay-700" data-testid="topic-tree-error" role="alert">
        Couldn&apos;t load topics.{" "}
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="underline underline-offset-2 hover:text-clay-900"
            data-testid="topic-tree-retry"
          >
            Retry
          </button>
        ) : null}
      </div>
    );
  }
  const roots = Array.isArray(topics) ? topics : [];
  if (roots.length === 0) {
    return (
      <p className="mt-2 text-xs text-slate-500" data-testid="topic-tree-empty">
        No topics for this subject yet.
      </p>
    );
  }
  return (
    <ul className="mt-2 border-t border-slate-100 pt-1" data-testid="topic-tree">
      {roots.map((node) => (
        <TopicNode key={node.topic_id} node={node} depth={0} />
      ))}
    </ul>
  );
}

SubjectTopicTree.propTypes = {
  topics: PropTypes.arrayOf(PropTypes.shape(NODE_SHAPE)),
  loading: PropTypes.bool,
  error: PropTypes.bool,
  onRetry: PropTypes.func,
};
