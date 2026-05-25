import React, { useMemo } from "react";
import Combobox from "./Combobox";
import useCmsList from "./useCmsList";

/**
 * Cascade-aware adapter: turns a `type: "ref"` ENTITY_CONFIG field into a
 * searchable picker backed by a CMS list endpoint.
 *
 * `field.ref` shape:
 *   {
 *     endpoint: "exam-cycles",        // CMS list endpoint
 *     labelKey: "cycle_name",         // human-readable label
 *     secondaryKey: "year",           // optional secondary text
 *     filters: { exam_id: "exam_id" } // queryParam -> sibling form field
 *   }
 *
 * The `filters` map reads sibling values out of `formValues`, so when the
 * parent field changes the child list refetches with the new param. The
 * filter object is rebuilt every render, but react-query compares query
 * keys structurally, so only a real value change triggers a refetch.
 */
export default function CmsRefField({ field, value, formValues = {}, onChange, testId }) {
  const ref = field.ref || {};
  const filterMap = ref.filters || {};

  const filters = {};
  for (const [param, formKey] of Object.entries(filterMap)) {
    filters[param] = formValues[formKey];
  }

  const { items, loading } = useCmsList(ref.endpoint, filters);

  const options = useMemo(
    () =>
      items.map((it) => ({
        id: it.id,
        label: it[ref.labelKey] || it.name || it.id,
        secondary: ref.secondaryKey ? it[ref.secondaryKey] : undefined,
      })),
    [items, ref.labelKey, ref.secondaryKey],
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
