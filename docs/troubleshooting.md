# Troubleshooting

Start with `python3 install.py doctor --live` from your source checkout. For an
issue report, use `python3 install.py doctor --json`; that report intentionally
excludes paths and session content. Describe your terminal/shell setup separately.

| Symptom/check | What to do |
|---|---|
| No Session Status sidebar | Enable View → Toggle Toolbelt, then View → Toolbelt → Session Status. |
| Launcher opens, status stays idle | In a fresh Codex CLI session, open `/hooks` and review/trust the plugin. Submit a short prompt. |
| `codex` / `codex_plugins` | Update Codex CLI to 0.153.4+. Rerun with `--codex /absolute/path/to/codex` if needed. |
| `iterm_status` / `iterm_version` | Update to iTerm2 3.7+. Use `--iterm-app /absolute/path/iTerm.app` for custom locations. |
| `iterm_api` / `iterm_connection` | Open iTerm, enable its Python API in Settings → General → Magic, and allow the it2 request if prompted. Run `doctor --live` again. |
| `hook_python` | Rerun the installer with a working Python 3.9+. This refreshes the saved interpreter after Python/pyenv upgrades. |
| `profile_default` / `profile_workspace` | Rerun installation; diagnostics found a missing, duplicate, or edited launcher entry. Backups preserve the previous file. |
| `source_link` | Run the installer from the checkout referenced by `~/plugins/iterm2-status`. Reconcile a conflicting checkout before reinstalling. |
| `workspace` | Restore the saved directory, use a new `--workspace`, or remove that launcher with `--no-workspace`. |
| `installed_plugin` | Run `python3 install.py` after pulling or switching versions. Source edits alone do not update Codex's cache. |
| Another installer is running | Wait for that process to finish, then retry. A leftover lock file is harmless; locking belongs to the process, not the filename. |
| Configuration changed during install | Another process edited a file. Review that file and retry; the installer refuses to overwrite the changed snapshot. |
| Codex installation failed | Follow Codex's error, then rerun this installer. Existing launchers were preserved. The error names the backup directory. |

## Discovery and environment

The installer records its actual Python executable in `python-path` alongside
`settings.json`. The hook reads that path as data, never as a sourced shell script.
`CODEX_ITERM2_PYTHON` overrides it for an advanced/custom launch environment.

The iTerm utility is found through `CODEX_ITERM2_IT2`, a saved `--iterm-app`, `PATH`,
`~/.iterm2/it2`, an optional Claude integration link, and standard/per-user app
folders. An invalid explicit override produces a diagnostic error instead of
silently selecting another app. Hook errors remain observational and quiet.

Selected Codex/shell/search paths are kept beside the settings file. The launcher's
login shell loads the chosen shell's startup files; the saved search path also
helps npm-installed Codex find Node. Rerun installation when moving an executable.

Keep `CODEX_HOME` and `XDG_CONFIG_HOME` consistent between installation and Codex
launches. Changing Codex homes selects another Codex installation/configuration.
Custom remote iTerm preference URLs cannot be checked from the local plist;
`doctor --live` checks the actual connection instead.

## Backups and removal

Changed files are copied into timestamped private folders under
`~/.config/codex-iterm2-status/backups/` (or the selected XDG config directory).
The active Codex configuration is backed up before plugin installation. Backups can
contain sensitive settings; do not attach them to a public issue.

The installer does not blindly restore an entire config file after an error:
other tools may have changed it. Fix the error and rerun, or compare the named
backup with the current file and restore only the intended settings.

Uninstall preserves the source, marketplace entry, local preferences, and backups.
It archives only this plugin's launcher profiles. This permits reinstall and
rollback without deleting unrelated configuration.
