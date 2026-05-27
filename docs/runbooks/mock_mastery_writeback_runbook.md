# Runbook: Mock Mastery Write-back

- Set env `FF_MOCK_MASTERY_WRITES` to `off|shadow|live` and redeploy backend.
- In shadow: run
  - `python tools/mastery_shadow_analysis/shadow_analysis.py compare --days 14`
  - `python tools/mastery_shadow_analysis/shadow_analysis.py tasks-overlap --days 14`
- Rollback: execute rollback SQL from docs/study_os/mock_mastery_writeback.md.
