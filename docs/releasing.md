# Release procedure

1. Update the semantic version with `python3 tools/dev.py version --set VERSION`
   and add a dated changelog entry. Beta versions use `0.2.0-beta.1` style names.
2. Run `make test`. Install the source, review changed hooks, and complete the
   [live smoke test](#live-smoke-test). Commit the exact manifest that was tested.
3. Push the commit and require every Compatibility job to pass, including clean
   install jobs on Intel and Apple Silicon. Inspect failures; never skip a failing
   supported setup to produce a green release.
4. With a clean checkout, create an annotated tag `vVERSION` and run `make package`.
   The ZIP and adjacent SHA256 file are built from committed HEAD and must have a
   manifest matching the tested source. Existing tags are immutable.
5. Push the tag. Create a GitHub **prerelease** for beta versions, attach the ZIP
   and checksum, and include changes, compatibility evidence, and known limits.
6. Verify the published tag's commit and downloaded archive checksum. On a public
   repository, also verify access without GitHub authentication.

The repository-owned tooling uses only Python's standard library and Git. Codex's
optional development cache suffix (`+codex.TIMESTAMP`) can be present in the
manifest; release tags and filenames use the semantic version before `+`. The
archive still contains the full exact manifest version.

`tools/ci_install.py` is restricted to fresh GitHub-hosted macOS runners. It downloads
checksum-pinned official Codex and iTerm archives, then checks install, repeat
install, upgrade, rollback, diagnostics, and repeat uninstall without any account
or model request. Update the pinned upstream versions/checksums deliberately, with
source links and both architectures tested.

## Live smoke test

Use a disposable native iTerm tab and an ordinary Codex CLI session. Do not create
subagents solely to test; use the process fixtures for concurrent subagent events.

- Confirm startup is idle and a prompt/tool changes it to working.
- Trigger an actual harmless approval request. Confirm waiting, then working after
  approval/tool completion, then idle after the final response.
- Interrupt a task; confirm idle. Exit normally; confirm the row clears.
- Resume the same session; confirm old waiting/background state does not reappear.
- Open the default and workspace launcher profiles; verify the working directories.
- Keep another native tab/pane open; verify updates target only the owning UUID.
- Run `doctor --live` and save only the redacted check report for release evidence.

Record exact macOS/architecture, Python, Codex, iTerm and plugin versions, the
observed sequence, and any limitations in `docs/compatibility.md`.
