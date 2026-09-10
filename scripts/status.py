#!/usr/bin/env python3
"""Report Codex lifecycle events to iTerm2 without influencing agent decisions."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

# Also support importlib-based embedding by the installer and test tools.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from iterm_support import find_it2

EVENTS = (
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PermissionRequest",
    "PostToolUse", "PreCompact", "PostCompact", "SubagentStart",
    "SubagentStop", "Stop", "Interrupt", "SessionEnd",
)
COLORS = {"working": "#e5a950", "waiting": "#e06c75", "idle": "#98c379", "": ""}
INPUT_TOOLS = {"request_user_input", "request_user_input_async"}


def terminal_id(value):
    """Accept iTerm's w0t0p0:UUID form, but never the implicit active session."""
    candidate = value.rsplit(":", 1)[-1]
    if re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", candidate):
        return candidate.upper()
    return None


def clean(value, limit=80):
    return " ".join(str(value or "").split())[:limit]


def tool_key(event):
    # Keep neither prompts nor tool arguments in the status cache.
    tool = event.get("tool_name")
    payload = event.get("tool_input")
    # PermissionRequest adds a description that PostToolUse omits. The shell or
    # patch command is the stable identifier across those two event shapes.
    if tool in {"Bash", "apply_patch", "Edit", "Write"} and isinstance(payload, dict) and "command" in payload:
        payload = {"command": payload["command"]}
    raw = json.dumps([tool, payload], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def transition(previous, event):
    """Return new state, or None for an event that does not own this terminal."""
    name = event.get("hook_event_name")
    sid = event.get("session_id")
    if name not in EVENTS or not isinstance(sid, str) or not sid:
        return None
    state = dict(previous)
    if state.get("session_id") == sid and state.get("event") == "SessionEnd" and name not in {"SessionStart", "UserPromptSubmit"}:
        return None
    if state.get("session_id") != sid:
        if state and name not in {"SessionStart", "UserPromptSubmit"}:
            return None
        state = {"session_id": sid, "working": False, "agents": [], "waiting": {}}
    state["agents"] = list(state.get("agents", []))
    state["waiting"] = dict(state.get("waiting", {}))
    state["project"] = clean(Path(event.get("cwd") or ".").name)
    state["event"] = name
    state["updated_at"] = time.time()
    agent = event.get("agent_id")
    tool = clean(event.get("tool_name"), 50)

    if name == "UserPromptSubmit":
        state.update(working=True, waiting={})
    elif name in {"PreCompact", "PostCompact"}:
        state["working"] = True
    elif name == "SessionStart" and event.get("source") == "compact":
        state["working"] = True
    elif name == "PreToolUse":
        state["working"] = True
        if tool in INPUT_TOOLS:
            state["waiting"][tool_key(event)] = "Input needed"
    elif name == "PermissionRequest":
        state["waiting"][tool_key(event)] = "Approval needed" + (f" ({tool})" if tool else "")
    elif name == "PostToolUse":
        state["waiting"].pop(tool_key(event), None)
    elif name == "SubagentStart" and isinstance(agent, str) and agent not in state["agents"]:
        state["agents"].append(agent)
    elif name == "SubagentStop" and agent in state["agents"]:
        state["agents"].remove(agent)
    elif name == "Stop":
        state.update(working=False, waiting={})
    elif name in {"Interrupt", "SessionEnd"}:
        state.update(working=False, waiting={}, agents=[])

    if name == "SessionEnd":
        status, detail = "", ""
    elif state["waiting"]:
        status, detail = "waiting", "Codex · " + next(iter(state["waiting"].values()))
    elif state["working"] or state["agents"]:
        status, detail = "working", "Codex · " + state["project"]
        if state["agents"]:
            detail += f" · {len(state['agents'])} subagent(s)"
    else:
        status, detail = "idle", "Codex · " + state["project"]
    state.update(status=status, detail=detail)
    return state


def report(event):
    terminal = terminal_id(os.environ.get("ITERM_SESSION_ID", ""))
    if not terminal or os.environ.get("TERM_PROGRAM") != "iTerm.app":
        return
    it2 = find_it2()
    if not it2:
        return
    data = Path(os.environ.get("PLUGIN_DATA") or (Path.home() / ".cache/codex-iterm2-status"))
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    state_path = data / f"{terminal}.json"
    lock_path = data / f"{terminal}.lock"
    with os.fdopen(os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600), "w") as lock:
        # Do not hold up an agent if another event's iTerm request stalls.
        deadline = time.monotonic() + 0.5
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    return
                time.sleep(0.01)
        try:
            previous = json.loads(state_path.read_text())
            if not isinstance(previous, dict):
                previous = {}
        except (OSError, ValueError):
            previous = {}
        state = transition(previous, event)
        if state is None:
            return
        color = COLORS[state["status"]]
        # Explicit UUID is essential: a hook must never update the focused tab.
        command = [it2, "session", "set-status", "--session", terminal,
                   "--status", state["status"], "--dot-color", color,
                   "--text-color", color, "--detail", state["detail"],
                   "--background-tasks", str(len(state["agents"]))]
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=1.0, check=False)
            state["reported"] = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            state["reported"] = False
        # Retain SessionEnd as a tombstone so late events cannot reclaim this tab.
        fd, tmp = tempfile.mkstemp(prefix=f".{terminal}.", dir=data)
        try:
            with os.fdopen(fd, "w") as output:
                json.dump(state, output)
                output.write("\n")
            os.replace(tmp, state_path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


def main():
    try:
        event = json.loads(sys.stdin.read(2 * 1024 * 1024))
        if isinstance(event, dict):
            report(event)
    except Exception:
        # Status is observational. Never block a tool, approve it, or alter prompts.
        pass
    print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
