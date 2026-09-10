# Changelog

## 0.2.0-beta.1 — 2026-09-10 (in preparation)

- Discover standard, per-user, and custom iTerm installations without requiring Claude.
- Remember Python, Codex, and shell paths; support bash/zsh/fish launcher choices,
  custom Codex/XDG config locations, and custom local iTerm preferences.
- Check prerequisite versions and actual status-command capabilities before install.
- Diagnose missing/edited/duplicate launcher profiles, broken source links and
  interpreters; provide optional live checks and redacted JSON support reports.
- Serialize installs, preserve launchers after CLI installation failures, and make
  uninstall repeatable even when the cached plugin has already been removed.
- Save concurrent lifecycle transitions before contacting iTerm. Coalesce reports,
  track identical concurrent approvals, clear resumed-session state, and reject
  late Stop/Interrupt events from older turns.
- Add macOS Intel/Apple Silicon CI, multiple Python versions, and clean installation
  jobs using real checksum-verified Codex and iTerm binaries.
- Include independent development/version/package tools, support documentation,
  an issue form, a labeled status illustration, and MIT licensing.

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
