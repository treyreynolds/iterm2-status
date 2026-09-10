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
- [ ] License choice from owner and a release with checksummed download.
- [ ] Local live status, launcher, approval, completion, and resume verification.
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
- MIT prepared as the stated default while the owner's optional license preference
  question remains unanswered. No visibility change or release has been performed.
- Remaining: rerun expanded CI with actual bash/zsh/fish profile execution; install
  the beta in the canonical source checkout and perform live hook/launcher smoke
  tests; finalize evidence and release notes, package, publish, and verify access.
