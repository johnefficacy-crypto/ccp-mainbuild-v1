import React, { Suspense, lazy } from "react";
import PropTypes from "prop-types";
import MarkdownSafe from "./MarkdownSafe";
import { hasMath } from "./mathSegments";

// KaTeX (JS + CSS) lives only in this lazy chunk, fetched the first time a
// string with real math delimiters renders. Currency `$` never triggers it —
// see the delimiter rules in ./mathSegments.js.
const KatexBlock = lazy(() => import("./_katexRuntime"));

export { hasMath };

export default function MathRenderer({ text, dir = "auto", className, inline = false }) {
  if (!hasMath(text || "")) return <MarkdownSafe text={text} dir={dir} className={className} inline={inline} />;
  return (
    <Suspense fallback={<MarkdownSafe text={text} dir={dir} className={className} inline={inline} />}>
      <KatexBlock text={text} dir={dir} className={className} inline={inline} />
    </Suspense>
  );
}

MathRenderer.propTypes = {
  text: PropTypes.string,
  dir: PropTypes.string,
  className: PropTypes.string,
  inline: PropTypes.bool,
};
