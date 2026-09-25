import React, { useMemo } from "react";
import PropTypes from "prop-types";
import { renderMarkdown } from "./markdown";

/**
 * Sanitised GFM markdown (tables, emphasis, lists, line breaks). Raw HTML in
 * `text` is shown as text, never interpreted; output passes a tight DOMPurify
 * allowlist (see ./markdown.js). Single-paragraph text renders inline in a
 * <span> so it sits inside option buttons and labelled rows without adding
 * block margins; multi-block text (tables, lists, paragraphs) renders in a <div>.
 *
 * `renderMath` is supplied only by the lazy KaTeX runtime (via MathRenderer);
 * without it any `$…$` math is shown as its source.
 */
export default function MarkdownSafe({ text, className, dir = "auto", inline = false, renderMath = null }) {
  const { html, block } = useMemo(
    () => renderMarkdown(text || "", { inline, renderMath }),
    [text, inline, renderMath]
  );
  const Tag = block ? "div" : "span";
  return <Tag className={className} dir={dir} dangerouslySetInnerHTML={{ __html: html }} />;
}

MarkdownSafe.propTypes = {
  text: PropTypes.string,
  className: PropTypes.string,
  dir: PropTypes.string,
  inline: PropTypes.bool,
  renderMath: PropTypes.func,
};
