import React from "react";
import MarkdownSafe from "./MarkdownSafe";

export default function KatexRuntime({ text, dir = "auto" }) {
  return <MarkdownSafe text={text} dir={dir} />;
}
