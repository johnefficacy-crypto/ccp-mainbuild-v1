import React, { useId } from "react";

// Level values from migration 028 CHECK constraint.
const TOPIC_LEVELS = ["topic", "microtopic", "concept"];

// default_difficulty_level has no DB CHECK constraint — free text.
// These are the conventional values used across the system.
const DIFFICULTY_LEVELS = ["easy", "medium", "hard"];

/**
 * Renders all 8 editable fields for a topic row.
 * Props: topic, siblings (same-subject topics for parent picker),
 *        dirtyFields (Set), onFieldChange(name, value)
 */
export default function TopicFieldsForm({ topic, siblings, dirtyFields, onFieldChange }) {
  const uid = useId();
  const id = (name) => `${uid}-${name}`;

  function field(name) {
    return {
      id: id(name),
      "data-dirty": dirtyFields.has(name) ? "true" : undefined,
    };
  }

  function handleMetaBlur(e) {
    const raw = e.target.value.trim();
    if (!raw) { onFieldChange("metadata", null); return; }
    try {
      onFieldChange("metadata", JSON.parse(raw));
    } catch {
      // leave as-is; TopicFieldsForm surfaces the error via aria-describedby
      e.target.setCustomValidity("Invalid JSON");
      e.target.reportValidity();
    }
  }

  function handleMetaChange(e) {
    e.target.setCustomValidity("");
    onFieldChange("metadata", e.target.value); // keep raw string while typing
  }

  const metaValue =
    topic.metadata === null || topic.metadata === undefined
      ? ""
      : typeof topic.metadata === "string"
      ? topic.metadata
      : JSON.stringify(topic.metadata, null, 2);

  return (
    <div className="space-y-4">
      {/* name */}
      <div>
        <label htmlFor={id("name")} className="block text-sm font-medium text-gray-700 mb-1">
          Name <span aria-hidden="true" className="text-red-500">*</span>
        </label>
        <input
          {...field("name")}
          type="text"
          value={topic.name || ""}
          onChange={(e) => onFieldChange("name", e.target.value)}
          required
          aria-required="true"
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* slug */}
      <div>
        <label htmlFor={id("slug")} className="block text-sm font-medium text-gray-700 mb-1">
          Slug <span aria-hidden="true" className="text-red-500">*</span>
        </label>
        <input
          {...field("slug")}
          type="text"
          value={topic.slug || ""}
          onChange={(e) => onFieldChange("slug", e.target.value)}
          required
          aria-required="true"
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <p className="text-xs text-gray-500 mt-1">Must be unique within the subject. Server validates.</p>
      </div>

      {/* level */}
      <div>
        <label htmlFor={id("level")} className="block text-sm font-medium text-gray-700 mb-1">
          Level
        </label>
        <select
          {...field("level")}
          value={topic.level || ""}
          onChange={(e) => onFieldChange("level", e.target.value)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">— select —</option>
          {TOPIC_LEVELS.map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
      </div>

      {/* parent_topic_id */}
      <div>
        <label htmlFor={id("parent_topic_id")} className="block text-sm font-medium text-gray-700 mb-1">
          Parent topic
        </label>
        <select
          {...field("parent_topic_id")}
          value={topic.parent_topic_id || ""}
          onChange={(e) => onFieldChange("parent_topic_id", e.target.value || null)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">— none —</option>
          {siblings.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <p className="text-xs text-gray-500 mt-1">
          Scoped to the same subject. Cross-subject reparenting is not permitted.
        </p>
      </div>

      {/* default_difficulty_level */}
      <div>
        <label htmlFor={id("default_difficulty_level")} className="block text-sm font-medium text-gray-700 mb-1">
          Default difficulty
        </label>
        <select
          {...field("default_difficulty_level")}
          value={topic.default_difficulty_level || ""}
          onChange={(e) => onFieldChange("default_difficulty_level", e.target.value || null)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">— unset —</option>
          {DIFFICULTY_LEVELS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {/* description */}
      <div>
        <label htmlFor={id("description")} className="block text-sm font-medium text-gray-700 mb-1">
          Description
        </label>
        <textarea
          {...field("description")}
          rows={3}
          value={topic.description || ""}
          onChange={(e) => onFieldChange("description", e.target.value || null)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* is_active */}
      <div className="flex items-center gap-3">
        <input
          {...field("is_active")}
          type="checkbox"
          checked={topic.is_active ?? true}
          onChange={(e) => onFieldChange("is_active", e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-indigo-600"
        />
        <label htmlFor={id("is_active")} className="text-sm font-medium text-gray-700">
          Active
        </label>
      </div>

      {/* metadata */}
      <div>
        <label htmlFor={id("metadata")} className="block text-sm font-medium text-gray-700 mb-1">
          Metadata (JSON)
        </label>
        <textarea
          {...field("metadata")}
          rows={4}
          defaultValue={metaValue}
          key={metaValue}
          onChange={handleMetaChange}
          onBlur={handleMetaBlur}
          aria-describedby={id("metadata-hint")}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
          spellCheck={false}
        />
        <p id={id("metadata-hint")} className="text-xs text-gray-500 mt-1">
          Valid JSON object. Validated on blur.
        </p>
      </div>
    </div>
  );
}
