# Codex iTerm2 Status

This repository is the canonical source for the `iterm2-status` Codex plugin.
iTerm2 supplies the native Session Status sidebar. No daemon or MCP service is needed.

- Read README.md before changing install behavior.
- Run `make test` after changing runtime or installer code.
- Hooks must remain observational: return `{}`, exit 0, and never grant approval,
  block a tool, add model context, or store prompts/commands/tool output.
- Target an explicit iTerm session UUID. Never default to the active tab.
- Keep workspace paths, local profile choices, caches, backups, and credentials
  outside the repository. The installer saves machine-specific choices separately.
- Preserve unrelated marketplace and iTerm profile entries during install/update.
- Edit source here, not Codex's installed cache. Reinstall after source changes.
- For local plugin iteration, follow the plugin-creator skill's cachebuster/reinstall
  workflow when that skill is available. For releases, commit the actual manifest
  version and changelog before tagging and packaging.
- Run a live CLI approval/completion smoke test when lifecycle mapping changes.
  Do not create subagents just to test; use the existing fixtures for concurrency.
- Check `git remote -v` before publishing. Follow docs/releasing.md and update
  docs/compatibility.md with observed evidence. Do not imply fixture tests are live GUI tests.
- Repository-owned development helpers live in tools/dev.py; keep them usable
  without an installed Codex skill bundle.
