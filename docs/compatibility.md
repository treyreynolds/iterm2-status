# Compatibility and test evidence

Last checked: 2026-09-10. The beta targets local Codex CLI sessions in native iTerm
windows, tabs, and split panes, with one foreground Codex session per pane.

## Verified automation

The beta's 48 tests passed on these real GitHub-hosted macOS runners:

| macOS | CPU | Python | Evidence |
|---|---|---|---|
| 14 | Apple Silicon | 3.9 | Unit, hook-process, and syntax tests |
| 15 | Intel | 3.9 and 3.14 | Unit, hook-process, and syntax tests |
| 15 | Apple Silicon | 3.11 | Unit, hook-process, and syntax tests |
| 26 | Apple Silicon | 3.14 | Unit, hook-process, and syntax tests |

[Candidate run](https://github.com/treyreynolds/iterm2-status/actions/runs/34497385839)
passed all seven jobs. Use the
[Compatibility workflow](https://github.com/treyreynolds/iterm2-status/actions/workflows/ci.yml)
for current results.

Real Codex 0.153.4 and iTerm2 3.7.0 clean-runner installation passed on both Intel
and Apple Silicon in [run 34497385839](https://github.com/treyreynolds/iterm2-status/actions/runs/34497385839).
It verified repeat installation, upgrade, rollback, diagnostics, preservation of
unrelated profiles, and repeat uninstall. The same run passed all 48 automated
tests across the five Python/macOS combinations. These jobs do not exercise the
GUI or generate model conversations. Both architectures also executed generated
bash, zsh, and fish profile commands, launched the real Codex version command,
and returned to the selected shell. The source path included spaces, quotes, and
literal shell metacharacters.

## Local live evidence

The original 0.1.0 release was verified on Apple Silicon macOS 26.3 with iTerm2
3.7.0 and Codex CLI 0.153.4: launcher startup, ordinary CLI launch, prompt/tool
activity, actual approval, completion, and session exit.

The beta (`0.2.0-beta.1+codex.20260910154219`) was installed and tested on Apple
Silicon macOS 26.3, Python 3.14.3, iTerm2 3.7.0, and Codex CLI 0.154.0. A real CLI
conversation ran in a controlled PTY with its iTerm UUID explicitly bound to a
disposable native iTerm window. The plugin's saved states and successful live API
reports confirmed actual approval → waiting, approved tool completion → working,
final response → idle, interrupt → idle, and normal exit → cleared. Resuming the
same conversation emitted SessionStart → idle, then prompt → working and Stop →
idle, without restoring old waiting state. All live diagnostic checks passed;
hook trust was inspected separately in Codex's `/hooks` UI.

Both default and saved-workspace profiles also opened actual native iTerm windows
with Codex 0.154.0 and the expected inherited/configured working directory. The
disposable windows were closed after verification.

This is API and CLI evidence, not a visual inspection of every sidebar row.
Subagent tracking has process/concurrency tests; it has not been verified with
live delegated agents.

## Setup coverage

- Standard `/Applications`, per-user `~/Applications`, and explicit custom iTerm
  app paths; a Claude integration symlink is an optional discovery hint.
- Python 3.9–3.14 compatibility, including a saved interpreter outside `PATH`.
- Explicit Codex executable paths and saved shell search paths.
- bash/zsh/fish launcher configuration, quoted and Unicode paths, saved workspace
  preferences, and custom local iTerm preference folders.
- Existing marketplace/profile preservation, repeated installs, configuration
  backups, failed Codex installation, and concurrent installer exclusion.
- `CODEX_HOME` and `XDG_CONFIG_HOME` location handling.

Automated fixtures of a setup do not prove every Homebrew/pyenv/shell version works.
Report a failing setup with the redacted diagnostic report so the matrix can grow.

## Current limits

- iTerm2 3.7's macOS minimum is 13. macOS 13 is not part of the hosted test matrix.
- Codex 0.153.4 is the CI baseline; 0.154.0 has the local live evidence above. Newer versions must retain the required
  plugin and lifecycle interfaces; the installer checks CLI capabilities.
- Codex desktop conversations and other terminal emulators are outside this integration.
- Ordinary CLI startup/resume can defer SessionStart until the first submitted
  prompt. The supplied launcher sets an initial idle status itself.
- SSH, containers, and tmux/screen are not verified. Multiplexed processes can share
  the same inherited iTerm UUID; use native iTerm panes for independent rows.
- Denied approvals can remain “waiting” until a subsequent Stop or Interrupt when
  Codex emits no matching tool completion. No transcript polling is used to guess.
- Abruptly killed ordinary CLI sessions cannot emit SessionEnd. The supplied
  launcher clears status when its Codex process returns. Terminal closure removes
  its row; killing the launcher itself can bypass cleanup.
- iTerm failures are best effort. State transitions are saved before network/API
  requests, but a failed or timed-out report may remain stale until the next event.
