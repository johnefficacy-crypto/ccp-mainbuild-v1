# Claude Code Instructions

## Verbosity and Token Efficiency

- **No planning narration.** Do not announce what you are about to do before doing it ("Now I'll update the checklist...", "Now write the PR plan..."). Just do it.
- **No step-by-step commentary.** Do not narrate each tool call or describe the sequence of actions you are taking. Let tool calls speak for themselves.
- **No redundant context-setting.** Do not restate what you just read or what you are about to read. Skip phrases like "Now I have enough context" or "Let me append to...".
- **Parallel work silently.** When doing multiple things in parallel, do not announce them. Run the tool calls and report results only if something notable happened.
- **One-sentence updates only.** If you must communicate mid-task, one sentence max. State results, not intentions.
- **End-of-turn summary only.** After completing work, give one or two sentences: what changed and what's next.
