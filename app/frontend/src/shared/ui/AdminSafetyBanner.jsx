import React, { useId, useState } from "react";
import { ChevronDown, ShieldAlert } from "lucide-react";

// Shared admin safety banner — styled after the prototype's persona warning
// (red-dashed rose card). Both /admin/persona and /admin/exam-intelligence
// previously inlined near-identical markup; this keeps the safety copy
// consistent and in one place.
export default function AdminSafetyBanner({
  title,
  children,
  icon: Icon = ShieldAlert,
  testId,
  tone = "rose",
  collapsible = false,
  defaultOpen = false,
}) {
  const [open, setOpen] = useState(defaultOpen);
  const generatedId = useId().replace(/:/g, "");
  const contentId = `admin-safety-banner-${generatedId}-content`;
  const toggleTestId = testId ? `${testId}-toggle` : undefined;
  const contentTestId = testId ? `${testId}-content` : undefined;
  const toneClass =
    tone === "rose"
      ? "border-dashed border-[#D9B4A6] bg-[#F2DDD6]"
      : "border border-[#E7DECB] bg-[#FBF8F2]";
  const iconColor = tone === "rose" ? "text-[#7A3925]" : "text-clay-700";
  const titleColor = tone === "rose" ? "text-[#7A3925]" : "text-clay-900";
  const bodyColor = tone === "rose" ? "text-[#7A3925]/85" : "text-clay-700";

  if (!collapsible) {
    return (
      <div
        role="note"
        className={`relative overflow-hidden rounded-[18px] border ${toneClass} p-4 flex items-start gap-3`}
        data-testid={testId}
      >
        <Icon className={`h-5 w-5 mt-0.5 ${iconColor}`} aria-hidden="true" />
        <div className="text-sm">
          <div className={`eyebrow ${titleColor === "text-[#7A3925]" ? "!text-[#7A3925]" : ""}`}>{title}</div>
          <div className={`mt-1.5 ${bodyColor}`}>{children}</div>
        </div>
      </div>
    );
  }

  return (
    <div
      role="note"
      className={`relative overflow-hidden rounded-[18px] border ${toneClass} p-4 flex items-start gap-3`}
      data-testid={testId}
    >
      <Icon className={`h-5 w-5 mt-0.5 ${iconColor}`} aria-hidden="true" />
      <div className="text-sm flex-1">
        <button
          type="button"
          className="group flex w-full items-center justify-between gap-3 text-left"
          aria-expanded={open}
          aria-controls={contentId}
          data-testid={toggleTestId}
          onClick={() => setOpen((current) => !current)}
        >
          <span className={`eyebrow ${titleColor === "text-[#7A3925]" ? "!text-[#7A3925]" : ""}`}>{title}</span>
          <ChevronDown
            className={`h-4 w-4 shrink-0 ${iconColor} transition-transform ${open ? "rotate-180" : ""}`}
            aria-hidden="true"
          />
        </button>
        <div id={contentId} data-testid={contentTestId} hidden={!open} className={`mt-1.5 ${bodyColor}`}>
          {children}
        </div>
      </div>
    </div>
  );
}
