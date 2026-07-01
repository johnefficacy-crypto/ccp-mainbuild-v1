---
description: Review-only observation of an open PR — critically examine the code, verify against contracted docs/repo, flag bugs and gaps, then comment on the PR and report the review comment ID.
argument-hint: <PR number>  (e.g. checkpost 823)
allowed-tools: mcp__github__pull_request_read, mcp__github__get_file_contents, mcp__github__get_commit, mcp__github__list_commits, mcp__github__add_issue_comment, mcp__github__pull_request_review_write, mcp__github__add_comment_to_pending_review, mcp__github__actions_list, mcp__github__actions_get, mcp__github__get_job_logs, Read, Grep, Glob
---

Perform a **review-only checkpost pass** on PR number **$ARGUMENTS** in `johnefficacy-crypto/ccp-mainbuild-v1`. If no number is given, run this pass for every currently open PR.

## What to look for
1. **Critical examination of the code fixed** — is the change correct, complete, and internally consistent?
2. **Verification against the contract** — check the PR diff against the relevant contracted doc(s) and the repo's stated intent (read order in CLAUDE.md: GRAPH_REPORT, ai-context, AGENTS, domain-model, the module doc for the area touched). Does the code actually satisfy what was contracted?
3. **Bugs** — logic errors, edge cases, RLS/verified-read violations, entity-canonicity mistakes (`recruitments` vs `exams`, `exam_id` vs `recruitment_id`), migration-discipline breaks.
4. **Gaps** — missing pieces, unhandled states, checklist/status not updated, tests or validation absent.
5. **Possible fixes** — describe what the fix would be. Describe only.

## Report
1. Post a single review comment on the **PR body/conversation** (`add_issue_comment`) summarizing findings under: Code Fixed, Contract Verification, Bugs, Gaps, Possible Fixes.
2. Capture the returned **review comment ID** and report it back in the chat.
3. **Send that comment ID as the payload** (echo it clearly as the final line, e.g. `PAYLOAD: comment_id=<id>`).

## Do NOT
- **Do NOT fix anything.** Do not edit files, do not commit, do not push, do not open or update code on the PR.
- Do not resolve review threads or merge the PR.
- Do not run `graphify`, migrations, or any mutating command.
- This is observation and reporting only — findings live in the PR comment, nothing else.
