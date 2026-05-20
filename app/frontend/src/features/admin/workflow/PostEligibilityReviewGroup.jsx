import React, { useState } from "react";

// Per-post eligibility review. Rendered as one compact row per post so a
// recruitment with many posts stays a short, scannable table instead of
// repeating a tall field-by-field card for every post (endless scroll).
//
// The only post-scoped promotion blocker is ``requires_domicile``, so that is
// the one interactive control here (a checkbox pre-filled from the scraper's
// extraction hint). The remaining post fields are shown read-only for context;
// fine-grained corrections happen in the full recruitment editor after promote.

const STATUS_BADGE = {
  verified: { cls: "badge resolved", text: "verified" },
  corrected: { cls: "badge info", text: "corrected" },
  rejected: { cls: "badge neutral", text: "flagged" },
  unverified: { cls: "badge pending", text: "needs check" },
};

function ageRange(post) {
  const min = post?.min_age;
  const max = post?.max_age;
  if (min == null && max == null) return "—";
  return `${min ?? "—"}–${max ?? "—"}`;
}

function listValue(v) {
  if (Array.isArray(v)) return v.join(", ") || "—";
  return v == null || v === "" ? "—" : String(v);
}

function unitValue(post) {
  const parts = [post?.unit_name || post?.unit_code, post?.unit_location_city, post?.unit_location_state]
    .filter(Boolean);
  return parts.length ? parts.join(" · ") : "—";
}

function findDomicileDetail(evidenceDetails, entityKey) {
  if (!Array.isArray(evidenceDetails)) return null;
  return evidenceDetails.find((d) =>
    (d?.field_name || "") === "requires_domicile"
    && (d?.entity_type || "").toLowerCase() === "post"
    && (d?.entity_key || "").trim().toLowerCase() === entityKey.toLowerCase()) || null;
}

function PostRow({ post, postIndex, evidenceDetails, onFieldAction }) {
  const entityKey = (post?.post_name || "").trim() || `post-${postIndex}`;
  const detail = findDomicileDetail(evidenceDetails, entityKey);
  const statusKey = detail?.reviewer_status || "unverified";
  const meta = STATUS_BADGE[statusKey] || STATUS_BADGE.unverified;
  const verified = statusKey === "verified";
  const baseValue = detail?.corrected_value != null ? detail.corrected_value : Boolean(post?.requires_domicile);
  const [checked, setChecked] = useState(Boolean(baseValue));

  const scope = { entity_type: "post", entity_key: entityKey };

  const toggle = (next) => {
    setChecked(next);
    onFieldAction("requires_domicile", "correct", next, scope);
  };

  return (
    <tr data-testid={`post-row-${postIndex}`}>
      <td>
        <div className="row-ttl">{post?.post_name || `Post #${postIndex + 1}`}</div>
        <div className="row-sub">post {postIndex}</div>
      </td>
      <td className="num">{post?.vacancies ?? "—"}</td>
      <td className="num">{ageRange(post)}</td>
      <td>{listValue(post?.education_required)}</td>
      <td>{listValue(post?.disciplines)}</td>
      <td>{unitValue(post)}</td>
      <td>
        <label className="row" style={{ gap: 6, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => toggle(e.target.checked)}
            data-testid={`post-domicile-${postIndex}`}
            aria-label={`Requires state domicile for ${post?.post_name || `post ${postIndex}`}`}
          />
          <span className="anno">{checked ? "required" : "not required"}</span>
        </label>
      </td>
      <td><span className={meta.cls}>{meta.text}</span></td>
      <td>
        <button
          type="button"
          className="btn small"
          disabled={verified}
          onClick={() => onFieldAction("requires_domicile", "verify", null, scope)}
          data-testid={`post-verify-${postIndex}`}
        >
          {verified ? "Verified" : "Verify"}
        </button>
      </td>
    </tr>
  );
}

export default function PostEligibilityReviewGroup({ posts, evidenceDetails, onFieldAction }) {
  const list = Array.isArray(posts) ? posts : [];
  if (list.length === 0) {
    return <div className="anno" data-testid="post-eligibility-empty">No post-level records extracted.</div>;
  }
  return (
    <div data-testid="post-eligibility-review">
      <div className="anno" style={{ marginBottom: 6 }}>
        Confirm the domicile requirement per post (pre-filled from the scraped notification). Other fields are shown for context.
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="t">
          <thead>
            <tr>
              <th>Post</th>
              <th>Vacancies</th>
              <th>Age</th>
              <th>Education</th>
              <th>Disciplines</th>
              <th>Unit</th>
              <th>Domicile?</th>
              <th>Status</th>
              <th> </th>
            </tr>
          </thead>
          <tbody>
            {list.map((post, postIndex) => (
              <PostRow
                key={postIndex}
                post={post}
                postIndex={postIndex}
                evidenceDetails={evidenceDetails}
                onFieldAction={onFieldAction}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
