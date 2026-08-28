import React from "react";
import { useSearchParams } from "react-router-dom";
import ThemeSelector from "../../features/study/essay/ThemeSelector";
import IdeaCanvas from "../../features/study/essay/IdeaCanvas";

// Essay Idea Canvas page. Route: /app/study/essay — mounted UNDER StudyShell,
// absent from the sidebar (no-new-surface rule), entered via an in-app link.
// The selected theme lives in ?theme= so the canvas is deep-linkable and the
// selector step is skippable once a theme is chosen.
export default function EssayIdeaCanvas() {
  const [params, setParams] = useSearchParams();
  const themeId = params.get("theme") || "";
  const themeName = params.get("theme_name") || "";

  const pick = (id, name) => {
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("theme", id);
      if (name) next.set("theme_name", name);
      else next.delete("theme_name");
      return next;
    });
  };

  const clear = () => {
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete("theme");
      next.delete("theme_name");
      return next;
    });
  };

  if (!themeId) {
    return <ThemeSelector onPick={pick} />;
  }

  return (
    <section className="space-y-3" data-testid="essay-idea-canvas-page">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl">Essay Idea Canvas</h1>
        <button
          type="button"
          onClick={clear}
          className="text-xs text-slate-500 hover:text-slate-800"
          data-testid="essay-change-theme"
        >
          ← Change theme
        </button>
      </div>
      <IdeaCanvas themeId={themeId} themeLabel={themeName} />
    </section>
  );
}
