"""Dependency checks and a deliberately small, shareable diagnostic schema."""

import os
from pathlib import Path
import platform
import subprocess
import sys

from iterm_support import (MIN_CODEX, MIN_ITERM, MIN_PYTHON, executable,
                           find_it2, iterm_preferences, iterm_version, version_tuple)


def check(identifier, ok, message, warning=False):
    return {"id": identifier, "status": "ok" if ok else ("warning" if warning else "error"),
            "message": message}


def probe(command, timeout=10):
    # Child output can contain user paths or terminal titles. Never include it in
    # exceptions or the shareable report; report only a named check and remediation.
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def prerequisites(home, settings):
    checks = [check("platform", sys.platform == "darwin", "macOS is required for iTerm2."),
              check("python", sys.version_info[:2] >= MIN_PYTHON, "Python 3.9 or later is required.")]
    versions = {"os": platform.mac_ver()[0] or platform.system(), "architecture": platform.machine(),
                "python": platform.python_version()}
    codex = executable(settings.get("codex") or "codex")
    output = probe([codex, "--version"]) if codex else None
    version = version_tuple(output)
    versions["codex"] = ".".join(map(str, version)) if version else None
    checks.append(check("codex", bool(version and version >= MIN_CODEX),
                        "Install Codex CLI 0.153.4 or later; use --codex PATH if it is outside PATH."))
    capability = probe([codex, "plugin", "add", "--help"]) if version else None
    checks.append(check("codex_plugins", capability is not None,
                        "Codex must support the plugin add command."))
    it2 = find_it2(home, settings=settings)
    try:
        version = version_tuple(iterm_version(it2))
    except (OSError, ValueError):
        version = None
    versions["iterm"] = ".".join(map(str, version)) if version else None
    checks.append(check("iterm_version", version is None or version >= MIN_ITERM,
                        "iTerm2 3.7 or later is required."))
    capability = probe([it2, "session", "set-status", "--help"]) if it2 else None
    checks.append(check("iterm_status", bool(capability and all(flag in capability for flag in
                        ["--session", "--status", "--detail", "--background-tasks"])),
                        "Install iTerm2 3.7+; for a custom location use --iterm-app /path/iTerm.app."))
    try:
        enabled = bool(iterm_preferences(home).get("EnableAPIServer"))
        checks.append(check("iterm_api", enabled,
                            "Enable iTerm2 Settings > General > Magic > Python API.", warning=True))
    except (OSError, ValueError):
        checks.append(check("iterm_api", False,
                            "Saved iTerm preferences could not be read; use doctor --live to check access.", warning=True))
    return checks, versions, codex, it2


def live_check(it2):
    output = probe([it2, "session", "list"], timeout=10) if it2 else None
    return check("iterm_connection", output is not None,
                 "Open iTerm2, enable its Python API, and allow the it2 connection if prompted.")


def display(report, as_json=False):
    if as_json:
        import json
        print(json.dumps(report, indent=2))
    else:
        print("Codex iTerm2 Status diagnostics")
        for key, value in report["versions"].items():
            print(f"  {key}: {value or 'unknown'}")
        for item in report["checks"]:
            print(f"{item['status'].upper()}: {item['id']}: {item['message']}")
        print("Review hook trust with /hooks in a fresh Codex session.")
    return 1 if any(c["status"] == "error" for c in report["checks"]) else 0
