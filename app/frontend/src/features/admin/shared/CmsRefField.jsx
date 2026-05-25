import React, { useMemo } from "react";
import Combobox from "./Combobox";
import useCmsList from "./useCmsList";

/**
 * Cascade-aware adapter: turns a `type: "ref"` ENTITY_CONFIG field into a
 * searchable picker backed by a CMS list endpoint.
 *
 * `field.ref` shape:
 *   {
 *     endpoint: "exam-cycles",         // CMS list endpoint
 *     labelKey: "cycle_name",          // human-readable label
 *     secondaryKey: "year",            // optional secondary text
 *     filters: { exam_id: "exam_id" }, // queryParam -> sibling form field
 *     staticFilters: { level: "topic" }// queryParam -> constant value
 *   }
 *
 * The `filters` map reads sibling values out of `formValues`, so when the
 * parent field changes the child list refetches with the new param.
 * `staticFilters` are constant query params (e.g. restrict a parent picker
 * to level=topic). The filter object is rebuilt every render, but
 * react-query compares query keys structurally, so only a real value change
 * triggers a refetch.
 */
export default function CmsRefField({ field, value, formValues = {}, onChange, testId }) {
  const ref = field.ref || {};
  const filterMap = ref.filters || {};

  const filters = { ...(ref.staticFilters || {}) };
  for (const [param, formKey] of Object.entries(filterMap)) {
    filters[param] = formValues[formKey];
  }

  const { items, loading } = useCmsList(ref.endpoint, filters);

  // ``valueField`` is the column written into the form (default the row id —
  // e.g. ``storage_path`` for a document picker). ``displayFields`` joins
  // several columns into the option label.
  const valueField = ref.valueField || "id";
  const options = useMemo(
    () =>
      items.map((it) => ({
        id: it[valueField],
        label: ref.displayFields
          ? ref.displayFields.map((f) => it[f]).filter(Boolean).join(" · ") || it[valueField]
          : it[ref.labelKey] || it.name || it[valueField],
        secondary: ref.secondaryKey ? it[ref.secondaryKey] : undefined,
      })),
    [items, valueField, ref.labelKey, ref.secondaryKey, ref.displayFields],
  );

  return (
    <Combobox
      value={value || ""}
      onChange={onChange}
      options={options}
      loading={loading}
      placeholder={`Search ${ref.endpoint}…`}
      testId={testId}
    />
  );
}
