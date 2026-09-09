import argparse
import importlib.util
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Installer(unittest.TestCase):
    def test_marketplace_preserves_existing_plugins_and_metadata(self):
        original = {"name": "mine", "interface": {"displayName": "My tools"},
                    "plugins": [{"name": "another", "source": {"source": "local", "path": "./another"}}]}
        result = installer.marketplace_config(original)
        self.assertEqual(original["plugins"], result["plugins"][:1])
        self.assertEqual(result["interface"], original["interface"])
        self.assertEqual(installer.marketplace_config(result), result)
        self.assertEqual(len(original["plugins"]), 1)

    def test_source_conflict_is_rejected(self):
        data = {"name": "personal", "plugins": [{"name": "iterm2-status", "source": {"source": "local", "path": "./someone-else"}}]}
        with self.assertRaises(ValueError):
            installer.marketplace_config(data)

    def test_profile_command_quotes_spaces_apostrophes_and_shell_syntax(self):
        root = Path("/tmp/O'Reilly tools/$(must-not-run)/iterm2-status")
        profiles = installer.profile_config(root, {"parent_profile": "Default"}, {"Profiles": []})
        command = shlex.split(profiles["Profiles"][0]["Command"])
        self.assertEqual(command[:2], ["/bin/zsh", "-lic"])
        nested = shlex.split(command[2])
        self.assertEqual(nested, ["exec", "/bin/zsh", str(root / "scripts/launch.zsh")])

    def test_workspace_stays_out_of_shell_command(self):
        workspace = "/tmp/O'Reilly/$(not-a-command)"
        settings = {"parent_profile": "Default", "workspace": workspace, "workspace_name": "Codex — Test"}
        profiles = installer.profile_config(Path("/tmp/iterm2-status"), settings, {"Profiles": []})
        profile = profiles["Profiles"][1]
        self.assertEqual(profile["Working Directory"], workspace)
        self.assertNotIn(workspace, profile["Command"])

    def test_profiles_preserve_unrelated_entries_and_migrate_old_launchers(self):
        custom = {"Name": "Custom", "Guid": "unrelated"}
        old = {"Name": "Codex", "Guid": "TREY-CODEX-AGENT-0001"}
        result = installer.profile_config(ROOT, {"parent_profile": "Default"}, {"Profiles": [custom, old]})
        self.assertEqual(result["Profiles"][0], custom)
        self.assertEqual(len(result["Profiles"]), 2)
        self.assertEqual(result["Profiles"][1]["Name"], "Codex")

    def test_save_refuses_concurrent_changes_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "profiles.json"
            backup = Path(temp) / "backups"
            path.write_text('{"old":true}')
            with self.assertRaises(RuntimeError):
                installer.save_json(path, {}, backup, "a different snapshot")
            self.assertEqual(path.read_text(), '{"old":true}')
            installer.save_json(path, {"new": True}, backup, path.read_text())
            self.assertEqual(json.loads((backup / path.name).read_text()), {"old": True})

    def test_repeat_install_preserves_settings_and_marketplace(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            paths = installer.locations(home, ROOT)
            args = argparse.Namespace(workspace=str(home), workspace_name="Work", parent_profile="AI Chat",
                                      no_workspace=False, dry_run=False)
            with patch.object(installer.shutil, "which", return_value="/fake/codex"), patch.object(installer, "run") as run:
                installer.install(paths, args)
                first_marketplace = paths["marketplace"].read_bytes()
                first_profiles = paths["profiles"].read_bytes()
                args.workspace = args.workspace_name = args.parent_profile = None
                installer.install(paths, args)
                self.assertEqual(paths["marketplace"].read_bytes(), first_marketplace)
                self.assertEqual(paths["profiles"].read_bytes(), first_profiles)
                self.assertEqual(read_settings(paths)["workspace"], str(home.resolve()))
                self.assertEqual(run.call_count, 2)
                self.assertEqual(paths["canonical"].resolve(), ROOT)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            args = argparse.Namespace(workspace=None, workspace_name=None, parent_profile=None,
                                      no_workspace=False, dry_run=True)
            with patch.object(installer.shutil, "which", return_value="/fake/codex"), patch.object(installer, "run") as run:
                installer.install(installer.locations(home, ROOT), args)
                self.assertEqual(list(home.iterdir()), [])
                run.assert_not_called()

    def test_uninstall_archives_owned_profiles_and_keeps_source(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            paths = installer.locations(home, ROOT)
            paths["profiles"].parent.mkdir(parents=True)
            paths["profiles"].write_text(json.dumps({"Profiles": [{"Guid": installer.DEFAULT_GUID, "Name": "Codex"}]}))
            with patch.object(installer, "run"):
                installer.uninstall(paths, False)
            self.assertFalse(paths["profiles"].exists())
            self.assertEqual(len(list((paths["settings"].parent / "backups").glob("*/codex-profiles.json"))), 1)
            self.assertTrue(ROOT.is_dir())


def read_settings(paths):
    return json.loads(paths["settings"].read_text())


if __name__ == "__main__":
    unittest.main()
