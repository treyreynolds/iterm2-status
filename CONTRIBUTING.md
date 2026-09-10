# Contributing

Bug reports and small pull requests are welcome. Include the reproduction steps,
expected/observed status, and `python3 install.py doctor --json` output. Do not
include conversation transcripts, credentials, or full configuration backups.

## Development

Use macOS, Python 3.9+, and Git. No Python packages are required:

```sh
make test
python3 tools/dev.py validate
```

Tests invoke real hook processes with controlled fake iTerm commands, covering
privacy, timeouts, concurrency, and terminal isolation. Installer tests use
isolated temporary directories. GitHub CI adds real upstream CLI installation on
fresh Intel and Apple Silicon runners.

For local source changes, refresh the installed plugin version and reinstall:

```sh
python3 tools/dev.py version --dev
python3 install.py
```

Start a new Codex session and review changed hooks with `/hooks`. If working
inside Codex with its plugin-creator skill, use that skill's marketplace validation
and cachebuster/reinstall workflow; it has the same version-suffix convention.
Do not edit Codex's installed cache or rewrite unrelated marketplace entries.

Keep hooks observational: return `{}`, exit successfully, and never grant approval,
block a tool, inject model context, or store prompts/raw tool arguments/output.
Always target an explicit iTerm UUID. Add regression coverage for behavioral fixes.
A change to lifecycle mapping also needs the documented live smoke test.

Runtime dependencies should remain in Python's standard library. Keep machine
paths and preferences outside Git. Preserve unrelated user settings on every
installer path, including failures and repeated operations.

See [the release procedure](docs/releasing.md) for tagging, packaging, and checks.
