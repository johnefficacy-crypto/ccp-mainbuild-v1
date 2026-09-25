/**
 * English verbal drills — route /app/study/english-drills.
 *
 * Mounted UNDER StudyShell + inside RouteErrorBoundary and ABSENT from the
 * sidebar (no-new-surface rule); entered from the Learning hub card, the same
 * drill-in pattern as Improvement Lab / Essay canvas / Answer writing.
 * Client-only: sample question bank + localStorage progress, no API calls.
 */
import React from "react";

import EnglishDrillsSurface from "../../features/study/english-drills/EnglishDrills";

export default function EnglishDrills() {
  return (
    <section data-testid="english-drills-page" aria-label="English verbal drills">
      <EnglishDrillsSurface />
    </section>
  );
}
