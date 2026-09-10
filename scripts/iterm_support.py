"""Shared discovery for the installer and observational hooks (stdlib only)."""

import json
import os
from pathlib import Path
import plistlib
import re
import shutil

MIN_CODEX = (0, 153, 4)
MIN_ITERM = (3, 7, 0)
MIN_PYTHON = (3, 9)


def config_dir(home=None, environ=None):
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    base = Path(environ.get("XDG_CONFIG_HOME") or home / ".config").expanduser()
    if not base.is_absolute():
        raise ValueError("XDG_CONFIG_HOME must be an absolute directory.")
    return base / "codex-iterm2-status"


def load_settings(home=None, environ=None):
    path = config_dir(home, environ) / "settings.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("settings.json must contain an object.")
    return value


def executable(value):
    if not value:
        return None
    value = os.path.expanduser(str(value))
    candidate = shutil.which(value)
    return str(Path(candidate).absolute()) if candidate else None


def find_it2(home=None, environ=None, settings=None):
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    override = environ.get("CODEX_ITERM2_IT2")
    if override:
        return executable(override)
    settings = load_settings(home, environ) if settings is None else settings
    if settings.get("iterm_app"):
        return executable(Path(settings["iterm_app"]) / "Contents/Resources/utilities/it2")
    candidates = [shutil.which("it2"), home / ".iterm2/it2"]
    # The Claude integration is optional; its link is just another discovery hint.
    cc = home / ".config/iterm2/cc-status"
    try:
        if cc.is_symlink():
            candidates.append(cc.resolve().parent / "it2")
    except (OSError, RuntimeError):
        pass
    for directory in [home / "Applications", Path("/Applications")]:
        candidates.append(directory / "iTerm.app/Contents/Resources/utilities/it2")
        candidates.extend(p / "Contents/Resources/utilities/it2" for p in sorted(directory.glob("*iTerm*.app")))
    return next((found for value in candidates if (found := executable(value))), None)


def iterm_version(it2):
    if not it2:
        return None
    for parent in Path(it2).resolve().parents:
        if parent.suffix == ".app":
            with (parent / "Contents/Info.plist").open("rb") as stream:
                return plistlib.load(stream).get("CFBundleShortVersionString")
    return None


def version_tuple(value):
    match = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)", str(value))
    return tuple(map(int, match.groups())) if match else None


def iterm_preferences(home):
    """Read local or iTerm's configured custom preferences, without mutating them."""
    path = Path(home) / "Library/Preferences/com.googlecode.iterm2.plist"
    if not path.exists():
        return {}
    with path.open("rb") as stream:
        prefs = plistlib.load(stream)
    if prefs.get("LoadPrefsFromCustomFolder") and prefs.get("PrefsCustomFolder"):
        folder = str(prefs["PrefsCustomFolder"])
        if "://" in folder:
            raise ValueError("Remote iTerm preferences cannot be checked locally; use doctor --live.")
        custom = Path(folder).expanduser() / path.name
        with custom.open("rb") as stream:
            prefs = dict(prefs, **plistlib.load(stream))
    return prefs
