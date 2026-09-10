# Public beta work record

Completed 2026-09-10. Release: v0.2.0-beta.1, source commit 0ee17ade47a58698ec6832a53044190cfd8ff94c.
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
- [x] Release with checksummed download.
- [x] Publish beta and verify anonymous access to code and release assets.

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
- Final candidate CI 34508248499 and main CI 34509069756 passed all seven jobs
  on release commit 0ee17ade47a58698ec6832a53044190cfd8ff94c.
- Published [v0.2.0-beta.1](https://github.com/treyreynolds/iterm2-status/releases/tag/v0.2.0-beta.1)
  as a prerelease; verified annotated tag target, 49,158-byte ZIP, and checksum.
  Anonymous downloads matched SHA256
  `4477f30fd05386468cc231b9c61c55aaec8c08e2e1adf7cb10acc5e804d79b5d`.
- Anonymous repository API confirmed public visibility and MIT licensing.
  GitHub private vulnerability reporting is enabled; bug-report form is available.
- Extracted archive passed source validation. All 59 historical blobs were checked
  for common credential patterns and personal home paths, with no matches.
- Disposable test windows and the test-directory trust entry were cleaned up.
  Existing launcher preferences remain installed. The public beta objective is met;
  unverified environments are explicitly listed in docs/compatibility.md.
