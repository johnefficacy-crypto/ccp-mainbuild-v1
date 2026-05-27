import React from "react";

const fakeDOMPurify = {
  sanitize: (input = "") =>
    input
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;"),
};

export default function MarkdownSafe({ text, className, dir = "auto" }) {
  const clean = fakeDOMPurify.sanitize(text || "").replace(/\n/g, "<br />");
  return <span className={className} dir={dir} dangerouslySetInnerHTML={{ __html: clean }} />;
}
