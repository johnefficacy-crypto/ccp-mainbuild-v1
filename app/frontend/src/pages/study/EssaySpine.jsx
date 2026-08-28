import React from "react";
import { useParams } from "react-router-dom";

import EssaySpineScreen from "../../features/study/essay/EssaySpineScreen";

/**
 * Route entry for the Essay Spine.
 *
 * Mounted at `/app/study/essay/spine` with an optional `:themeId`, so the
 * screen can be deep-linked for one essay or opened cold to pick one up.
 */
export default function EssaySpine() {
  const { themeId } = useParams();
  return <EssaySpineScreen themeId={themeId || null} />;
}
