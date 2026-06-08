import { useEffect, useState } from "react";
import { api } from "../../lib/api";

/**
 * Returns active exam options for use in a <select>.
 * Each item: { value: slug, label: name }
 * Falls back to [] on error so the field still renders (just empty).
 */
export default function useExamOptions() {
  const [options, setOptions] = useState([]);
  useEffect(() => {
    api.get("/api/exams?limit=100").then((res) => {
      const items = res?.items || [];
      setOptions(items.map((e) => ({ value: e.slug, label: e.name })));
    }).catch(() => {});
  }, []);
  return options;
}
