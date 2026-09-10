# Codex iTerm2 Status

A local Codex plugin that puts Codex CLI sessions beside Claude Code in iTerm2’s
native **Session Status** sidebar. Working, waiting, and idle states show which
agent needs attention; click a row to jump to its terminal.

This repository owns the Codex hooks and launcher installer. iTerm2 supplies the
sidebar. Keep iTerm2, Codex CLI, and this plugin updated separately.

## Install on a Mac

Requirements: macOS, **iTerm2 3.7+**, **Codex CLI with lifecycle hooks**, and Python 3.
Tested with iTerm2 3.7.0 and Codex CLI 0.153.4. Enable the Python API under iTerm2
Settings → General → Magic; the built-in Claude integration may have enabled it.

The repository is currently private. Authenticate Git with your GitHub account
(for example, `gh auth login` followed by `gh auth setup-git`), then clone it:

```sh
mkdir -p ~/plugins
git clone https://github.com/treyreynolds/iterm2-status.git ~/plugins/iterm2-status
cd ~/plugins/iterm2-status
python3 install.py
```

For an extracted ZIP, place its `iterm2-status` folder under `~/plugins` and run
`python3 install.py` from that folder.

The installer registers the plugin in your personal Codex marketplace, installs
it with the Codex CLI, and adds a **Codex** dynamic profile. It works with a cloned
repository or an extracted ZIP and has no pip dependencies. If your checkout is
elsewhere, it creates the canonical `~/plugins/iterm2-status` symlink, provided that
location is not already occupied by a different checkout.

For a second launcher that always starts in a particular workspace:

```sh
python3 install.py --workspace ~/work --workspace-name 'Codex — Work'
```

To inherit an existing iTerm appearance, add `--parent-profile 'Profile Name'`.
The default parent is **Default**. Preview with `--dry-run`.

Start a new Codex session after installation. If prompted, use **/hooks** to review
and trust this plugin’s hooks. The installer does not approve hooks or change
sandbox, model, or approval policies. Existing Codex sessions need to be restarted
or resumed to pick up the plugin.

## Upgrade

From a clone on the `main` branch:

```sh
cd ~/plugins/iterm2-status
git pull --ff-only
python3 install.py
python3 install.py doctor
```

`git pull --ff-only` stops if local history has diverged. The installer reapplies
the checked-out release and preserves saved workspace/profile preferences. For a
ZIP installation, extract the new release over the source directory and rerun the
installer. An iTerm2 or Codex upgrade does **not** fetch updates to this repository.

Start a fresh Codex session after upgrades, and review changed hooks if requested.
The hook source is your Git checkout; Codex runs a cached installation, so editing
source alone does not update that cache.

## Diagnose or remove

```sh
python3 install.py doctor
python3 install.py uninstall --dry-run
python3 install.py uninstall
```

Doctor checks source versus installed versions, the iTerm API setting, and launcher
files. It does not inspect prompts or change settings. Use `/hooks` to inspect trust,
and run a short Codex task to confirm live status after a major upstream upgrade.

Uninstall removes the cached Codex plugin and archives its launcher profiles. It
keeps the source repository, local settings, marketplace entry, and backups so you
can reinstall. Unrelated entries in the profile file are preserved.

## Where things live

| Content | Location |
|---|---|
| Versioned source | This repository |
| Personal marketplace | `~/.agents/plugins/marketplace.json` |
| Installed hooks | Codex’s versioned plugin cache |
| Workspace and appearance choices | `~/.config/codex-iterm2-status/settings.json` |
| Configuration backups | `~/.config/codex-iterm2-status/backups/` |
| iTerm launcher profiles | `~/Library/Application Support/iTerm2/DynamicProfiles/codex-profiles.json` |
| Live status metadata | The `PLUGIN_DATA` directory supplied by Codex |

Machine-specific directories, profile names, live status, and configuration backups
stay outside Git. The adapter stores IDs, a folder name, status, and hashed tool
identifiers. It neither stores nor displays prompts, tool commands, or outputs.

## Develop and release

```sh
make test
```

The tests cover lifecycle transitions, simultaneous waiting tools, subagents,
terminal isolation, concurrent events, iTerm failures/timeouts, and installer
preservation/quoting. Runtime code uses Python’s standard library.

For local development in Codex, use the **plugin-creator** skill to refresh the
manifest’s `+codex.<timestamp>` cache suffix and reinstall. Its helper lives at:

```sh
python3 ~/.codex/skills/.system/plugin-creator/scripts/read_marketplace_name.py
python3 ~/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py .
python3 install.py
```

For a release: choose a new semantic version for an actual feature/fix release,
update `CHANGELOG.md`, run tests, reinstall and smoke-test, then commit and tag it.
Commit the manifest version used by the tag. Tags make it possible to return to a
known build. This package’s first repository release is `v0.1.0`.

```sh
make package
```

This creates `dist/iterm2-status.zip` from the committed **HEAD**, excluding local
settings, untracked changes, Git internals, and ignored generated files. Commit the
release before packaging. The archive has an `iterm2-status/` top-level folder.

For rollback, commit or stash local work first. With a clean worktree, run
`git switch --detach v0.1.0` (or another known tag) in the installed checkout and
rerun `python3 install.py`. Return to `main` when ready to upgrade again.
Git protects source history; the installer backs up local configuration.

The source is maintained in [treyreynolds/iterm2-status](https://github.com/treyreynolds/iterm2-status),
currently a private personal repository. Tags preserve releases for future installs
and rollback. No public distribution license is granted by this repository yet.

## Behavior and limits

- The adapter always targets the terminal UUID from `ITERM_SESSION_ID`.
- Hooks return `{}` and exit successfully even if iTerm2 is unavailable. They never
  approve or block agent actions.
- Input/approval requests take priority over working status. Completed background
  subagents allow an idle parent to return to idle.
- Approval status clears when the matching tool completes. A denied request may
  remain waiting until Stop or Interrupt if no matching completion event is emitted.
- The supplied launcher reports idle immediately and clears status after CLI exit.
  Ordinary `codex` commands also use the hooks, but may first appear when Codex
  emits SessionStart at the first prompt. Abruptly killed ordinary CLI processes
  cannot report a final hook.
- Codex desktop-app conversations are outside this integration.

## References

- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [iTerm2 Session Status](https://iterm2.com/documentation-session-status.html)
- [iTerm2 Dynamic Profiles](https://iterm2.com/documentation-dynamic-profiles.html)
