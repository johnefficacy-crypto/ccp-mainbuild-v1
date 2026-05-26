import React, { Suspense, lazy } from "react";
import MarkdownSafe from "./MarkdownSafe";

const KatexBlock = lazy(() => import("./_katexRuntime"));

export const hasMath = (text = "") => /\$\$[^$]+\$\$|\$[^$]+\$/.test(text);

export default function MathRenderer({ text, dir = "auto" }) {
  if (!hasMath(text)) return <MarkdownSafe text={text} dir={dir} />;
  return (
    <Suspense fallback={<MarkdownSafe text={text} dir={dir} />}>
      <KatexBlock text={text} dir={dir} />
    </Suspense>
  );
}
