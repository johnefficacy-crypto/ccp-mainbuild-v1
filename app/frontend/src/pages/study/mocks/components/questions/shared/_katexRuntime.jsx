import React from "react";
import PropTypes from "prop-types";
import katex from "katex";
import "katex/dist/katex.min.css";
import MarkdownSafe from "./MarkdownSafe";

const escapeAttr = (s) =>
  String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// Stable module-level function so MarkdownSafe's memo is not invalidated.
// HTML-only output (no MathML) keeps the sanitiser allowlist small; the TeX
// source is exposed to assistive tech through role="math" + aria-label.
export function renderMath(tex, display) {
  const html = katex.renderToString(tex, {
    displayMode: !!display,
    throwOnError: false,
    trust: false,
    strict: "ignore",
    output: "html",
  });
  return `<span role="math" aria-label="${escapeAttr(tex)}">${html}</span>`;
}

export default function KatexRuntime({ text, dir = "auto", className, inline = false }) {
  return <MarkdownSafe text={text} dir={dir} className={className} inline={inline} renderMath={renderMath} />;
}

KatexRuntime.propTypes = {
  text: PropTypes.string,
  dir: PropTypes.string,
  className: PropTypes.string,
  inline: PropTypes.bool,
};
