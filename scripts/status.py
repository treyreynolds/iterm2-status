#!/usr/bin/env python3
"""Report Codex lifecycle events to iTerm2 without influencing agent decisions."""

import fcntl
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unicodedata

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
    value = "".join(c for c in str(value or "") if unicodedata.category(c) not in {"Cc", "Cf"} or c in "\n\r\t")
    return " ".join(value.split())[:limit]


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
    if name == "SessionStart" and event.get("source") != "compact":
        state.update(working=False, agents=[], waiting={}, turn_id=None)
    turn = event.get("turn_id")
    if name == "UserPromptSubmit" and isinstance(turn, str):
        state["turn_id"] = turn
    elif name in {"Stop", "Interrupt", "PreCompact", "PostCompact"} and turn and state.get("turn_id") and turn != state["turn_id"]:
        return None
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
            add_waiting(state, event, "Input needed")
    elif name == "PermissionRequest":
        add_waiting(state, event, "Approval needed" + (f" ({tool})" if tool else ""))
    elif name == "PostToolUse":
        key = tool_key(event)
        pending = state["waiting"].get(key)
        if isinstance(pending, dict) and pending.get("count", 1) > 1:
            state["waiting"][key] = dict(pending, count=pending["count"] - 1)
        else:
            state["waiting"].pop(key, None)
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
        pending = next(iter(state["waiting"].values()))
        description = pending["detail"] if isinstance(pending, dict) else pending
        status, detail = "waiting", "Codex · " + description
    elif state["working"] or state["agents"]:
        status, detail = "working", "Codex · " + state["project"]
        if state["agents"]:
            detail += f" · {len(state['agents'])} subagent(s)"
    else:
        status, detail = "idle", "Codex · " + state["project"]
    state.update(status=status, detail=detail)
    return state


def add_waiting(state, event, detail):
    key = tool_key(event)
    previous = state["waiting"].get(key)
    count = previous.get("count", 1) if isinstance(previous, dict) else (1 if previous else 0)
    state["waiting"][key] = {"detail": detail, "count": count + 1}


@contextmanager
def locked(path, timeout):
    with os.fdopen(os.open(path, os.O_CREAT | os.O_RDWR, 0o600), "w") as lock:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Status lock is busy")
                time.sleep(0.01)
        yield


def read_state(path):
    try:
        state = json.loads(path.read_text())
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(path, state):
    fd, tmp = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(state, output)
            output.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


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
    state_lock = data / f"{terminal}.lock"
    # Save each transition before contacting iTerm. A slow GUI request must not
    # drop another event's approval, completion, or subagent state update.
    with locked(state_lock, 0.4):
        previous = read_state(state_path)
        state = transition(previous, event)
        if state is None:
            return
        state.update(revision=previous.get("revision", 0) + 1, reported=False)
        write_state(state_path, state)
    deadline = time.monotonic() + 2.0
    with locked(data / f"{terminal}.report.lock", 1.0):
        while time.monotonic() < deadline:
            with locked(state_lock, 0.1):
                snapshot = read_state(state_path)
                if snapshot.get("reported"):
                    return
            color = COLORS[snapshot["status"]]
            command = [it2, "session", "set-status", "--session", terminal,
                       "--status", snapshot["status"], "--dot-color", color,
                       "--text-color", color, "--detail", snapshot["detail"],
                       "--background-tasks", str(len(snapshot["agents"]))]
            try:
                result = subprocess.run(command, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        timeout=min(0.8, max(0.05, deadline - time.monotonic())), check=False)
                reported = result.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                reported = False
            with locked(state_lock, 0.1):
                latest = read_state(state_path)
                if latest.get("revision") == snapshot.get("revision"):
                    latest["reported"] = reported
                    write_state(state_path, latest)
                    return
                # A later event arrived during the request. Report the current
                # state, never replace it with this older snapshot.


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
