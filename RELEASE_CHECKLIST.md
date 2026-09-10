# Public beta work record

State checked 2026-09-10. Target: v0.2.0-beta.1. Source branch: beta/0.2.0.
The objective is a public beta with useful support across common macOS setups.

- [ ] Portable Python and iTerm discovery; explicit prerequisite checks.
- [ ] Correct diagnostics, optional live connection check, redacted support output.
- [ ] Safe repeat install, upgrade, failed-install recovery, and uninstall.
- [ ] Runtime lifecycle and concurrent-event regression coverage.
- [ ] macOS Intel/Apple Silicon and multiple Python versions in GitHub CI.
- [ ] Fresh real Codex CLI installation in CI, independent of Claude configuration.
- [ ] Repository-owned development/version/package tools.
- [ ] Setup, troubleshooting, compatibility, privacy, contribution, and security docs.
- [ ] License choice from owner and a release with checksummed download.
- [ ] Local live status, launcher, approval, completion, and resume verification.
- [ ] Publish beta and verify anonymous access to code and release assets.

Evidence and remaining work will be recorded here before release. Unit tests of a
setup are distinguished from a real macOS/CLI test of that setup. Unsupported
remote or terminal-multiplexer paths must be explicit, without implying they work.
