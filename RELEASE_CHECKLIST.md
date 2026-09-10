# Public beta work record

State checked 2026-09-10. Target: v0.2.0-beta.1. Source branch: beta/0.2.0.
The objective is a public beta with useful support across common macOS setups.

- [x] Portable Python and iTerm discovery; explicit prerequisite checks.
- [x] Correct diagnostics, optional live connection check, redacted support output.
- [x] Safe repeat install, upgrade, failed-install recovery, and uninstall.
- [x] Runtime lifecycle and concurrent-event regression coverage.
- [x] macOS Intel/Apple Silicon and multiple Python versions in GitHub CI.
- [x] Fresh real Codex CLI installation in CI, independent of Claude configuration.
- [x] Repository-owned development/version/package tools.
- [x] Setup, troubleshooting, compatibility, privacy, contribution, and security docs.
- [x] MIT license using the stated default from the optional owner preference question.
- [x] Local live status, launcher, approval, completion, interruption, exit, and resume verification.
- [ ] Release with checksummed download.
- [ ] Publish beta and verify anonymous access to code and release assets.

Evidence and remaining work will be recorded here before release. Unit tests of a
setup are distinguished from a real macOS/CLI test of that setup. Unsupported
remote or terminal-multiplexer paths must be explicit, without implying they work.

## Evidence — 2026-09-10

- Initial five-runner CI: 34489222221, all passed (38 tests).
- Full runtime/installer suite: 48 tests passed locally and in five-runner CI.
- Real upstream clean-install CI: 34490729507, both Intel and Apple Silicon passed
  install/reinstall, version upgrade/rollback, diagnostics, and repeated uninstall.
- Documentation illustration rendered and visually inspected; explicitly labeled
  as an illustration rather than a screenshot of the actual application.
- Expanded CI: 34497385839, all seven jobs passed, including actual bash/zsh/fish
  launcher execution on Intel and Apple Silicon with real Codex 0.153.4.
- Installed beta manifest 0.2.0-beta.1+codex.20260910154219. Local macOS 26.3 arm64,
  Python 3.14.3, iTerm2 3.7.0, Codex 0.154.0: real approval waiting → tool working
  → final idle, interrupt idle, exit cleared, resumed SessionStart idle and prompt
  working → idle. Each state reported successfully through the live iTerm API.
  The CLI ran in a controlled PTY bound to its disposable native window UUID.
- Default and workspace profiles opened native windows with the expected working
  directory. Live doctor passed; hook trust reviewed separately in `/hooks`.
- MIT is the stated default. Release notes and compatibility evidence are ready.
- Remaining: final commit CI, package, publish, enable private security reporting,
  and verify anonymous access and the archive checksum.
