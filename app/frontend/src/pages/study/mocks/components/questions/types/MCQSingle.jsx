import React from "react";
import QuestionStem from "../shared/QuestionStem";
import OptionList from "../shared/OptionList";
import MarkdownSafe from "../shared/MarkdownSafe";
import MathRenderer from "../shared/MathRenderer";

// Printed order mirrors OptionList: display_order asc (NULLs last), stable.
function byDisplayOrder(a, b) {
  const ad = a?.display_order;
  const bd = b?.display_order;
  if (ad == null && bd == null) return 0;
  if (ad == null) return 1;
  if (bd == null) return -1;
  return ad - bd;
}

// Resolve a correct_option_id (a UUID) to its printed label + text so the
// review screen never shows a raw UUID to aspirants. Label logic mirrors
// OptionList: prefer the projected source_label, else option_index, else the
// positional A/B/C… letter.
function resolveCorrectOption(options, correctOptionId) {
  if (!correctOptionId || !Array.isArray(options)) return null;
  const ordered = [...options].sort(byDisplayOrder);
  const pos = ordered.findIndex((o) => o.id === correctOptionId);
  if (pos === -1) return null;
  const o = ordered[pos];
  const label = o.source_label || `${o.option_index || String.fromCharCode(65 + pos)}`;
  return { label: String(label).replace(/\.$/, ""), text: o.option_text || "" };
}

export default function MCQSingle({
  question,
  mode,
  value,
  onChange,
  disabled,
  showCorrect,
  showExplanation,
}) {
  const correct = showCorrect ? resolveCorrectOption(question.options, question.correct_option_id) : null;
  return (
    <div>
      <QuestionStem text={question.question_text} images={question.images} />
      <OptionList
        options={question.options}
        selected={value?.selected_option_id ? [value.selected_option_id] : []}
        disabled={disabled || mode === "review"}
        onSelect={(id) => onChange({ ...value, selected_option_id: id })}
      />
      {correct ? (
        <div className="mt-2 text-sm text-sage-800" data-testid="review-correct-answer">
          <span className="font-semibold">Correct answer: </span>
          {correct.label}. <MathRenderer text={correct.text} />
        </div>
      ) : null}
      {showExplanation && question.explanation ? <MarkdownSafe text={question.explanation} /> : null}
    </div>
  );
}
