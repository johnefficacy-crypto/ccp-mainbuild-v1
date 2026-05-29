import React from "react";
import MathRenderer from "./MathRenderer";

const TRUSTED = [window.location.hostname, "cdn.careercopilot.in"];

function safeUrl(src) {
  try {
    const u = new URL(src, window.location.origin);
    if (!["http:", "https:"].includes(u.protocol)) return null;
    return TRUSTED.includes(u.hostname) ? u.toString() : null;
  } catch {
    return null;
  }
}

export default function QuestionStem({ text, images = [] }) {
  return (
    <div dir="auto">
      <MathRenderer text={text || ""} />
      {images.map((img, i) => {
        const src = safeUrl(img?.url || img?.src || "");
        if (!src) return null;
        return <img key={i} src={src} alt={img?.alt || `question-image-${i + 1}`} style={{ maxWidth: "100%" }} />;
      })}
    </div>
  );
}
