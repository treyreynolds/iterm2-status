import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/status.py"
spec = importlib.util.spec_from_file_location("status", SCRIPT)
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)
UUID = "11111111-2222-3333-4444-555555555555"
UUID2 = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"


def event(name, **extra):
    return dict(session_id="root-session", cwd="/private/test-project", hook_event_name=name, **extra)


class Lifecycle(unittest.TestCase):
    def test_lifecycle_and_approval(self):
        state = status.transition({}, event("SessionStart"))
        self.assertEqual(state["status"], "idle")
        state = status.transition(state, event("UserPromptSubmit"))
        tool = dict(tool_name="Bash", tool_input={"command": "printf test"})
        state = status.transition(state, event("PreToolUse", **tool))
        state = status.transition(state, event("PermissionRequest", **tool))
        self.assertEqual(state["status"], "waiting")
        state = status.transition(state, event("PostToolUse", **tool))
        self.assertEqual(state["status"], "working")
        state = status.transition(state, event("Stop"))
        self.assertEqual(state["status"], "idle")
        state = status.transition(state, event("SessionEnd"))
        self.assertEqual(state["status"], "")
        self.assertIsNone(status.transition(state, event("PostToolUse", **tool)))

    def test_waiting_survives_unrelated_parallel_tool(self):
        state = status.transition({}, event("UserPromptSubmit"))
        blocked = dict(tool_name="Bash", tool_input={"command": "one"})
        other = dict(tool_name="Bash", tool_input={"command": "two"})
        state = status.transition(state, event("PermissionRequest", **blocked))
        for hook in ["PreToolUse", "PostToolUse"]:
            state = status.transition(state, event(hook, **other))
        self.assertEqual(state["status"], "waiting")
        state = status.transition(state, event("PostToolUse", **blocked))
        self.assertEqual(state["status"], "working")

    def test_real_codex_permission_description_is_not_part_of_identity(self):
        state = status.transition({}, event("UserPromptSubmit"))
        state = status.transition(state, event("PermissionRequest", tool_name="Bash",
            tool_input={"command": "printf CODEX_PERMISSION_TEST", "description": "Verify status"}))
        self.assertEqual(state["status"], "waiting")
        state = status.transition(state, event("PostToolUse", tool_name="Bash",
            tool_use_id="exec-123", tool_input={"command": "printf CODEX_PERMISSION_TEST"}))
        self.assertEqual(state["status"], "working")
        self.assertEqual(state["waiting"], {})

    def test_input_tool_and_interrupt(self):
        tool = dict(tool_name="request_user_input", tool_input={"questions": ["private question"]})
        state = status.transition({}, event("PreToolUse", **tool))
        self.assertEqual(state["status"], "waiting")
        self.assertNotIn("private question", json.dumps(state))
        state = status.transition(state, event("Interrupt"))
        self.assertEqual(state["status"], "idle")

    def test_background_agents_survive_parent_stop(self):
        state = status.transition({}, event("UserPromptSubmit"))
        for agent in ["a", "b"]:
            state = status.transition(state, event("SubagentStart", agent_id=agent))
        state = status.transition(state, event("Stop"))
        self.assertEqual(state["status"], "working")
        state = status.transition(state, event("SubagentStop", agent_id="a"))
        self.assertEqual(state["status"], "working")
        state = status.transition(state, event("SubagentStop", agent_id="b"))
        self.assertEqual(state["status"], "idle")

    def test_old_session_cannot_clear_replacement(self):
        state = status.transition({}, event("UserPromptSubmit"))
        replacement = dict(event("SessionStart"), session_id="new-session")
        state = status.transition(state, replacement)
        self.assertIsNone(status.transition(state, event("SessionEnd")))

    def test_compaction_keeps_session_working(self):
        state = status.transition({}, event("SessionStart", source="compact"))
        self.assertEqual(state["status"], "working")

    def test_terminal_id_is_explicit_uuid(self):
        self.assertEqual(status.terminal_id("w0t2p0:" + UUID), UUID)
        for invalid in ["", "active", "all", "$(touch bad)", UUID + ";x"]:
            self.assertIsNone(status.terminal_id(invalid))


class Process(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.fake = self.data / "it2"
        self.fake.write_text('#!' + sys.executable + '\nimport json,os,sys\nfrom pathlib import Path\nwith (Path(os.environ["PLUGIN_DATA"])/"calls.jsonl").open("a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n')
        self.fake.chmod(0o700)
        self.env = dict(os.environ, PLUGIN_DATA=str(self.data), CODEX_ITERM2_IT2=str(self.fake),
                        ITERM_SESSION_ID="w0t0p0:" + UUID, TERM_PROGRAM="iTerm.app")

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, payload, env=None):
        result = subprocess.run([sys.executable, str(SCRIPT)], input=payload,
                                text=True, capture_output=True, env=env or self.env, timeout=4)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "{}\n")
        self.assertEqual(result.stderr, "")

    def test_reports_exact_terminal_without_private_payload(self):
        self.run_hook(json.dumps(event("UserPromptSubmit", prompt="secret phrase")))
        args = json.loads((self.data / "calls.jsonl").read_text())
        self.assertEqual(args[args.index("--session") + 1], UUID)
        state = (self.data / f"{UUID}.json").read_text()
        self.assertNotIn("secret phrase", state)
        self.assertTrue(json.loads(state)["reported"])
        self.assertEqual((self.data / f"{UUID}.json").stat().st_mode & 0o777, 0o600)

    def test_missing_terminal_is_noop(self):
        self.run_hook(json.dumps(event("Stop")), dict(self.env, ITERM_SESSION_ID=""))
        self.assertFalse((self.data / "calls.jsonl").exists())

    def test_malformed_input_never_blocks(self):
        for payload in ["not json", "null", "[]", "{}"]:
            self.run_hook(payload)
        self.assertFalse((self.data / "calls.jsonl").exists())

    def test_failing_iterm_never_blocks(self):
        self.fake.write_text("#!/bin/sh\nexit 1\n")
        self.run_hook(json.dumps(event("Stop")))
        self.assertFalse(json.loads((self.data / f"{UUID}.json").read_text())["reported"])

    def test_iterm_timeout_never_blocks(self):
        self.fake.write_text("#!" + sys.executable + "\nimport time\ntime.sleep(8)\n")
        self.run_hook(json.dumps(event("Stop")))
        self.assertFalse(json.loads((self.data / f"{UUID}.json").read_text())["reported"])

    def test_two_terminal_states_are_isolated(self):
        self.run_hook(json.dumps(event("UserPromptSubmit")))
        self.run_hook(json.dumps(event("Stop")), dict(self.env, ITERM_SESSION_ID=UUID2))
        self.assertEqual(json.loads((self.data / f"{UUID}.json").read_text())["status"], "working")
        self.assertEqual(json.loads((self.data / f"{UUID2}.json").read_text())["status"], "idle")

    def test_concurrent_subagent_events_do_not_lose_updates(self):
        self.run_hook(json.dumps(event("UserPromptSubmit")))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(self.run_hook, [json.dumps(event("SubagentStart", agent_id=str(i))) for i in range(4)]))
        state = json.loads((self.data / f"{UUID}.json").read_text())
        self.assertEqual(set(state["agents"]), {"0", "1", "2", "3"})


if __name__ == "__main__":
    unittest.main()
