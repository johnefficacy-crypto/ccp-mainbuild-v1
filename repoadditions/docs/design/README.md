# UI concept mockups

Exploratory concept designs — not built into the app yet, not wired to any
backend. Source is `.dc.html` (Claude Design Component format, throwaway
preview markup, not React) plus `canvas.json` where multi-artboard. Each is
also published as a live click-through preview — open the URL to interact
with it before deciding whether to build it for real.

**These are not production code.** Real build = React 18 + Tailwind +
react-hook-form + TanStack Query + recharts (see `app/frontend/package.json`
for the actual stack). Treat `.dc.html` as a interaction/layout reference
only — colors, spacing, state transitions, which things drag onto what —
and re-implement fresh in the real component system, not a port.

## essay-idea-and-spine-builder/

Two-artboard concept for the `essay_brainstorm_blocks` schema (migration
265 — see `app/supabase/migrations/265_essay_theme_taxonomy.sql`):

1. **Idea Canvas** — freeform mind-map: essay topic in the center, 6 draggable
   "angle" branches (Economic, Social Equity, Governance, Global/Comparative,
   Historical, Personal), sticky notes drag anywhere. A Helpers panel on the
   right (vocabulary, quotes, books+authors, examples, stats-to-verify) lets
   a student drop reference material straight onto the canvas.
2. **Spine** — sequences hook → thesis → reorderable body paragraphs →
   closing thought, with per-slot target word counts (~50/50/175-each/100)
   and a live "planned words vs. 1000–1200 target" progress bar. Slots
   reject the wrong card type on drop (a hook can't land in the body).

Live preview: https://claude.ai/code/artifact/61b365c1-054a-4958-a36d-5e3e170a0e72

Quotes (Gandhi, Amartya Sen, Ambedkar) and books (Sen, Drèze & Sen, Joshi,
Banerjee & Duflo) in the Helpers panel are real and correctly attributed —
safe to reuse. Numeric stat helpers are deliberately left as `[VERIFY]`
prompts, not fabricated figures.

**Backend status**: `essay_brainstorm_blocks` table exists, unseeded, no
endpoints yet. Closest to build-ready of the three — schema already fits.

## calendar-study-planner/

Weekly drag-and-drop planner: 7-day grid (Mon–Fri 2h cap, Sat/Sun 4h cap),
14 GS1–4 topic blocks draggable between days and a backlog column, per-day
capacity bar (turns red over cap), and a "carried over" tag demoing the
buffer-rollover rule from the sprint-scheduler spec.

Live preview: https://claude.ai/code/artifact/b9df4609-7b33-4918-8884-61dc3e33d503

**Backend status**: no matching table/endpoint yet. The `study:plan_regen`
job and `app/study_os/planner` scoring already generate a prioritized
topic list server-side — this UI assumes that list gets a day assignment
(new column or new join table) and a manual-override write path, neither
of which exist yet.

## exam-study-roadmap/

Macro view, not a weekly grid: a single winding path across the full
exam cycle (Foundation → Build → Prelims-intensive → Mains-consolidation →
Interview), with clickable checkpoint/mock/exam-day nodes and a track
toggle (full journey / prelims-only / mains-only) that dims the
non-matching nodes.

Live preview: https://claude.ai/code/artifact/5696069b-fddd-4230-a08a-53b1dde6df37

Week numbers, dates and node content are sample data, not pulled from any
real exam calendar — no such calendar exists in the backend yet.

**Backend status**: no matching table/endpoint. Would need an exam-cycle /
phase model (start date, phase boundaries, milestone list) that nothing in
the schema currently represents.

## Handing these off to build

Per concept, give the build session: this folder's `Main.dc.html` (+
siblings), the live preview link, and the backend status note above. Point
it at `app/frontend/package.json` for the real stack and tell it explicitly
not to port the `.dc.html` markup — re-implement the interaction using the
app's existing components/design tokens. Suggested build order: essay tool
first (schema is ready), the other two need new backend work before a real
build, not just frontend.

## Status / next step

See `docs/status/PYQ-Tagging-and-Essay-Brainstorm-UI-Status-2026-08-25.md`.
