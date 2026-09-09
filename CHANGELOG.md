# Changelog

## 0.1.0 — 2026-09-09

- Codex lifecycle hooks feed iTerm2's native Session Status sidebar.
- Working, waiting, idle, interruption, exit cleanup, and background-subagent tracking.
- Approval-event normalization verified against Codex CLI 0.153.4.
- Portable installer, optional workspace profile, saved local preferences, backups,
  diagnostics, and uninstall support.
- Git source history and a reproducible ZIP package target.

Compatibility verified on macOS with iTerm2 3.7.0 and Codex CLI 0.153.4.
Status behavior was tested against real approval and completion events; concurrency
and subagent behavior are covered by automated tests.
