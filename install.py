#!/usr/bin/env python3
"""Install, inspect, or remove the local Codex/iTerm2 integration (stdlib only)."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

NAME = "iterm2-status"
DEFAULT_GUID = "CODEX-ITERM2-DEFAULT-0001"
WORKSPACE_GUID = "CODEX-ITERM2-WORKSPACE-0001"
OWNED_GUIDS = {DEFAULT_GUID, WORKSPACE_GUID, "TREY-CODEX-AGENT-0001", "TREY-CODEX-ABILITIE-0001"}


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def marketplace_config(existing):
    """Only add a missing entry; never replace another plugin or source."""
    data = json.loads(json.dumps(existing)) if existing is not None else {
        "name": "personal", "interface": {"displayName": "Personal"}, "plugins": []}
    if not isinstance(data, dict) or not re.fullmatch(r"[A-Za-z0-9_-]+", str(data.get("name", ""))):
        raise ValueError("The personal marketplace must have a valid name.")
    if not isinstance(data.get("plugins"), list) or not all(isinstance(p, dict) for p in data["plugins"]):
        raise ValueError("The marketplace plugins field must be an array.")
    matches = [p for p in data["plugins"] if p.get("name") == NAME]
    expected = {"source": "local", "path": f"./plugins/{NAME}"}
    if matches:
        if len(matches) != 1 or matches[0].get("source") != expected:
            raise ValueError("An existing iterm2-status entry points elsewhere; reconcile it first.")
    else:
        data["plugins"].append({"name": NAME, "source": expected,
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity"})
    return data


def profile_config(source, settings, previous):
    if not isinstance(previous, dict) or not isinstance(previous.get("Profiles"), list) or not all(isinstance(p, dict) for p in previous["Profiles"]):
        raise ValueError("The existing dynamic profile file is malformed; review it first.")
    launcher = source / "scripts/launch.zsh"
    shell_command = "exec /bin/zsh " + shlex.quote(str(launcher))
    command = "/bin/zsh -lic " + shlex.quote(shell_command)
    common = {"Dynamic Profile Parent Name": settings["parent_profile"],
              "Tags": ["ai", "codex", NAME], "Custom Command": "Yes", "Command": command}
    profiles = [dict(common, Name="Codex", Guid=DEFAULT_GUID, **{"Custom Directory": "Recycle"})]
    if settings.get("workspace"):
        profiles.append(dict(common, Name=settings["workspace_name"], Guid=WORKSPACE_GUID,
                             **{"Custom Directory": "Yes", "Working Directory": settings["workspace"]}))
    # This file belongs to the integration, but preserve any user-added entries.
    extras = [p for p in previous.get("Profiles", []) if p.get("Guid") not in OWNED_GUIDS]
    return dict(previous, Profiles=extras + profiles)


def save_json(path, data, backup_dir, expected):
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    current = path.read_text() if path.exists() else None
    if current != expected:
        raise RuntimeError(f"{path} changed during installation; retry after reviewing it.")
    if current == content:
        return
    if current is not None:
        backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(path, backup_dir / path.name)
        (backup_dir / path.name).chmod(0o600)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            output.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def locations(home, source):
    return {"source": source, "canonical": home / "plugins" / NAME,
            "marketplace": home / ".agents/plugins/marketplace.json",
            "profiles": home / "Library/Application Support/iTerm2/DynamicProfiles/codex-profiles.json",
            "settings": home / ".config/codex-iterm2-status/settings.json",
            "config": home / ".codex/config.toml"}


def doctor(paths):
    problems = []
    manifest = read_json(paths["source"] / ".codex-plugin/plugin.json", {})
    print("Source:", paths["source"])
    print("Source version:", manifest.get("version", "missing"))
    if not shutil.which("codex"):
        problems.append("Codex CLI is not in PATH.")
    else:
        run(["codex", "--version"])
        marketplace = marketplace_config(read_json(paths["marketplace"], None))["name"]
        response = run(["codex", "plugin", "list", "--marketplace", marketplace, "--json"], capture_output=True)
        matches = [p for p in json.loads(response.stdout).get("installed", []) if p.get("name") == NAME]
        if not matches or not matches[0].get("enabled"):
            problems.append("The plugin is not installed and enabled.")
        else:
            installed = matches[0]["version"]
            print("Installed version:", installed)
            if installed != manifest.get("version"):
                problems.append("Installed version differs from source; rerun python3 install.py.")
    preferences = Path.home() / "Library/Preferences/com.googlecode.iterm2.plist"
    if preferences.exists():
        with preferences.open("rb") as stream:
            api_enabled = plistlib.load(stream).get("EnableAPIServer", False)
        print("iTerm Python API setting:", "enabled" if api_enabled else "disabled")
        if not api_enabled:
            problems.append("Enable iTerm2 Settings > General > Magic > Python API.")
    else:
        problems.append("iTerm2 preferences were not found; open iTerm2 and enable its Python API.")
    for profile in read_json(paths["profiles"], {"Profiles": []})["Profiles"]:
        if profile.get("Guid") in OWNED_GUIDS:
            print("Launcher:", profile["Name"])
    if not paths["profiles"].exists():
        problems.append("Launcher profiles are missing; rerun python3 install.py.")
    for problem in problems:
        print("ACTION:", problem)
    print("Use /hooks in a new Codex session to review hook trust. This command does not change it.")
    return 1 if problems else 0


def install(paths, args):
    source = paths["source"]
    manifest = read_json(source / ".codex-plugin/plugin.json", {})
    if manifest.get("name") != NAME or not (source / "scripts/status.py").is_file():
        raise ValueError("Run this installer from the complete iterm2-status package.")
    if not shutil.which("codex"):
        raise ValueError("Install Codex CLI and make codex available in PATH first.")
    canonical = paths["canonical"]
    if (canonical.exists() or canonical.is_symlink()) and canonical.resolve() != source:
        raise ValueError(f"{canonical} already contains another checkout; keep or move it first.")
    texts = {key: path.read_text() if path.exists() else None
             for key, path in paths.items() if key in {"settings", "marketplace", "profiles"}}
    settings = json.loads(texts["settings"]) if texts["settings"] else {}
    settings.setdefault("parent_profile", "Default")
    settings.setdefault("workspace_name", "Codex — Workspace")
    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
        if not workspace.is_dir():
            raise ValueError(f"Workspace is not a directory: {workspace}")
        settings["workspace"] = str(workspace)
    if args.workspace_name:
        settings["workspace_name"] = args.workspace_name
    if args.parent_profile:
        settings["parent_profile"] = args.parent_profile
    if args.no_workspace:
        settings.pop("workspace", None)
    marketplace = marketplace_config(json.loads(texts["marketplace"]) if texts["marketplace"] else None)
    profiles = profile_config(canonical, settings, json.loads(texts["profiles"]) if texts["profiles"] else {"Profiles": []})
    selector = f"{NAME}@{marketplace['name']}"
    print("Install", manifest["version"], "from", source)
    print("Register", selector, "in", paths["marketplace"])
    print("Launchers:", ", ".join(p["Name"] for p in profiles["Profiles"] if p.get("Guid") in OWNED_GUIDS))
    if args.dry_run:
        print("Dry run: no files or settings changed.")
        return 0
    backup = paths["settings"].parent / "backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup.mkdir(parents=True, mode=0o700)
    if paths["config"].exists():
        shutil.copy2(paths["config"], backup / "codex-config.toml")
        (backup / "codex-config.toml").chmod(0o600)
    if not canonical.exists():
        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.symlink_to(source, target_is_directory=True)
    # Existing entries stay byte-for-byte unchanged during upgrades.
    if texts["marketplace"] is None or json.loads(texts["marketplace"]) != marketplace:
        save_json(paths["marketplace"], marketplace, backup, texts["marketplace"])
    run(["codex", "plugin", "add", selector])
    save_json(paths["profiles"], profiles, backup, texts["profiles"])
    save_json(paths["settings"], settings, backup, texts["settings"])
    print("Backups:", backup)
    print("Installed. Start a new Codex session; use /hooks if any hooks need review.")
    return 0


def uninstall(paths, dry_run):
    marketplace = marketplace_config(read_json(paths["marketplace"], None))["name"]
    path = paths["profiles"]
    previous = path.read_text() if path.exists() else None
    data = json.loads(previous) if previous else {"Profiles": []}
    retained = [p for p in data["Profiles"] if p.get("Guid") not in OWNED_GUIDS]
    if dry_run:
        print("Would uninstall", f"{NAME}@{marketplace}", "and archive only this integration's launchers.")
        return 0
    run(["codex", "plugin", "remove", f"{NAME}@{marketplace}"])
    if previous is not None:
        backup = paths["settings"].parent / "backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        if retained:
            save_json(path, dict(data, Profiles=retained), backup, previous)
        else:
            backup.mkdir(parents=True, mode=0o700)
            if path.read_text() != previous:
                raise RuntimeError("Profiles changed during uninstall; review them before archiving.")
            shutil.move(str(path), str(backup / path.name))
    print("Uninstalled. Source, saved preferences, marketplace entry, and backups were kept.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="install", choices=["install", "doctor", "uninstall"])
    parser.add_argument("--workspace", help="Optional directory for a second launcher (saved for upgrades)")
    parser.add_argument("--workspace-name", help="Name of the workspace launcher")
    parser.add_argument("--parent-profile", help="Existing iTerm profile to inherit; defaults to Default")
    parser.add_argument("--no-workspace", action="store_true", help="Remove the optional workspace launcher")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.workspace and args.no_workspace:
        parser.error("--workspace and --no-workspace cannot be used together")
    paths = locations(Path.home(), Path(__file__).resolve().parent)
    try:
        if args.action == "doctor":
            return doctor(paths)
        if args.action == "uninstall":
            return uninstall(paths, args.dry_run)
        return install(paths, args)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print("Error:", error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
