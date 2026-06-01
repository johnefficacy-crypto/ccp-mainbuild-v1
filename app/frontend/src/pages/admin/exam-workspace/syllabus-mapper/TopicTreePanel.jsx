import React, { useState } from "react";
import { Pencil } from "lucide-react";

function groupByTopic(proposals) {
  const map = {};
  for (const p of proposals) {
    if (!map[p.topic_id]) map[p.topic_id] = { topic_id: p.topic_id, matched_alias: p.matched_alias, proposals: [] };
    map[p.topic_id].proposals.push(p);
  }
  return Object.values(map);
}

function TopicItem({ group, selectedKeys, onToggle, onEdit }) {
  const [expanded, setExpanded] = useState(true);
  const topicLabel = group.matched_alias || group.topic_id;
  return (
    <li role="treeitem" aria-expanded={expanded} className="mb-1">
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 text-sm font-medium text-gray-700 hover:text-indigo-700 flex-1 text-left min-w-0"
        >
          <span className="text-xs shrink-0">{expanded ? "▾" : "▸"}</span>
          <span className="flex-1 truncate">{topicLabel}</span>
          <span className="text-xs text-gray-400 shrink-0">{group.proposals.length}</span>
        </button>
        {onEdit && (
          <button
            type="button"
            onClick={() => onEdit(group.topic_id)}
            aria-label={`Edit topic ${topicLabel}`}
            data-testid={`edit-topic-${group.topic_id}`}
            className="shrink-0 p-1 text-gray-400 hover:text-indigo-600 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      {expanded && (
        <ul className="ml-4 mt-0.5 space-y-0.5">
          {group.proposals.map((p) => {
            const selected = selectedKeys.has(p.client_proposal_key);
            return (
              <li key={p.client_proposal_key} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={() => onToggle(p.client_proposal_key)}
                  aria-label={`Select mention on page ${p.source_page}`}
                  data-testid={`topic-cb-${p.client_proposal_key}`}
                  className="rounded"
                />
                <span className="text-xs text-gray-600">
                  p.{p.source_page} — {(p.confidence_score * 100).toFixed(0)}%
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </li>
  );
}

export default function TopicTreePanel({ proposals, selectedKeys, onToggle, onEditTopic, currentPage }) {
  const [showAll, setShowAll] = useState(false);
  const filtered = showAll ? proposals : proposals.filter((p) => p.source_page === currentPage);
  const groups = groupByTopic(filtered);

  return (
    <div className="h-full overflow-y-auto p-3 text-sm" data-testid="topic-tree-panel">
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-gray-700">Topics</span>
        <button
          type="button"
          onClick={() => setShowAll((v) => !v)}
          className="text-xs text-indigo-600 hover:underline"
          data-testid="toggle-show-all"
        >
          {showAll ? "Current page" : "All pages"}
        </button>
      </div>
      {groups.length === 0 ? (
        <p className="text-gray-400 text-xs">No proposals{showAll ? "" : " on this page"}.</p>
      ) : (
        <ul role="tree" className="space-y-1">
          {groups.map((g) => (
            <TopicItem
              key={g.topic_id}
              group={g}
              selectedKeys={selectedKeys}
              onToggle={onToggle}
              onEdit={onEditTopic}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
