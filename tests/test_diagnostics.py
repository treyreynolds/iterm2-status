import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import diagnostics
import iterm_support as support
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Setup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="O'Reilly tools ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.paths = installer.locations(self.home, ROOT, {})
        self.app = self.home / 'Applications/iTerm Custom.app'
        self.it2 = self.app / 'Contents/Resources/utilities/it2'
        self.it2.parent.mkdir(parents=True)
        self.it2.write_text('#!/bin/sh\nprintf "%s\\n" "--session --status --detail --background-tasks"\n')
        self.it2.chmod(0o700)
        self.write_version('3.7.0')
        self.codex = self.home / 'codex cli'
        self.version = json.loads((ROOT / '.codex-plugin/plugin.json').read_text())['version']
        self.codex.write_text('#!' + sys.executable + '\nimport sys,json\n'
                              'if "--version" in sys.argv: print("codex-cli 0.153.4")\n'
                              'elif "--help" in sys.argv: print("plugin add help")\n'
                              'else: print(json.dumps({"installed":[{"name":"iterm2-status","enabled":True,"version":' + repr(self.version) + '}]}))\n')
        self.codex.chmod(0o700)
        self.settings = {'codex': str(self.codex), 'iterm_app': str(self.app),
                         'parent_profile': 'Default', 'workspace_name': 'Codex — Workspace'}
        self.paths['settings'].parent.mkdir(parents=True)
        self.paths['settings'].write_text(json.dumps(self.settings))
        self.paths['python_path'].write_text(sys.executable + '\n')
        self.paths['canonical'].parent.mkdir(parents=True)
        self.paths['canonical'].symlink_to(ROOT)
        self.paths['profiles'].parent.mkdir(parents=True)
        self.profiles = installer.profile_config(self.paths['canonical'], self.settings, {'Profiles': []})
        self.paths['profiles'].write_text(json.dumps(self.profiles))
        prefs = self.home / 'Library/Preferences/com.googlecode.iterm2.plist'
        prefs.parent.mkdir(parents=True)
        prefs.write_bytes(plistlib.dumps({'EnableAPIServer': True}))
        self.addCleanup(patch.stopall)
        patch.object(diagnostics.sys, 'platform', 'darwin').start()
        patch.dict(os.environ, {'CODEX_ITERM2_IT2': ''}).start()

    def write_version(self, value):
        (self.app / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleShortVersionString': value}))

    def doctor(self, live=False):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = installer.doctor(self.paths, as_json=True, live=live)
        report = json.loads(output.getvalue())
        self.assertNotIn(str(self.home), output.getvalue())
        return code, {c['id']: c['status'] for c in report['checks']}

    def test_healthy_installation_and_private_report(self):
        code, checks = self.doctor()
        self.assertEqual(code, 0)
        self.assertEqual(checks['profile_default'], 'ok')
        self.assertEqual(checks['hook_trust'], 'warning')

    def test_empty_profile_file_is_an_error(self):
        self.paths['profiles'].write_text('{"Profiles": []}')
        code, checks = self.doctor()
        self.assertEqual(code, 1)
        self.assertEqual(checks['profile_default'], 'error')

    def test_changed_command_and_duplicate_owned_profile_are_errors(self):
        self.profiles['Profiles'][0]['Command'] = '/bin/false'
        self.paths['profiles'].write_text(json.dumps(self.profiles))
        self.assertEqual(self.doctor()[1]['profile_default'], 'error')
        self.profiles['Profiles'].append(self.profiles['Profiles'][0])
        self.paths['profiles'].write_text(json.dumps(self.profiles))
        self.assertEqual(self.doctor()[1]['profile_default'], 'error')

    def test_missing_saved_interpreter_is_an_error(self):
        self.paths['python_path'].write_text(str(self.home / 'missing python'))
        self.assertEqual(self.doctor()[1]['hook_python'], 'error')

    def test_malformed_settings_report_does_not_echo_private_data(self):
        self.paths['settings'].write_text('private secret broken json')
        code, checks = self.doctor()
        self.assertEqual(code, 1)
        self.assertEqual(checks['configuration'], 'error')

    def test_supported_codex_version_and_iterm_capabilities_required(self):
        self.codex.write_text('#!/bin/sh\necho codex-cli 0.100.0\n')
        self.assertEqual(self.doctor()[1]['codex'], 'error')
        self.write_version('3.6.0')
        self.assertEqual(self.doctor()[1]['iterm_version'], 'error')
        self.it2.write_text('#!/bin/sh\necho unrelated-tool\n')
        self.assertEqual(self.doctor()[1]['iterm_status'], 'error')

    def test_live_connection_is_optional_and_failures_are_reported(self):
        with patch.object(diagnostics, 'probe', return_value=None):
            result = diagnostics.live_check(self.it2)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(self.doctor(live=True)[1]['iterm_connection'], 'ok')

    def test_user_app_discovery_without_claude_or_path(self):
        with patch.object(support.shutil, 'which', side_effect=lambda p: str(p) if p and Path(p).is_file() and os.access(p, os.X_OK) else None):
            self.assertEqual(support.find_it2(self.home, {}, {}), str(self.it2))

    def test_invalid_explicit_override_does_not_silently_select_other_app(self):
        self.assertIsNone(support.find_it2(self.home, {'CODEX_ITERM2_IT2': '/not/an/it2'}, {}))
        self.assertIsNone(support.find_it2(self.home, {}, {'iterm_app': '/not/an/app'}))

    def test_custom_local_iterm_preferences(self):
        folder = self.home / 'synced preferences'
        folder.mkdir()
        prefs = self.home / 'Library/Preferences/com.googlecode.iterm2.plist'
        prefs.write_bytes(plistlib.dumps({'LoadPrefsFromCustomFolder': True, 'PrefsCustomFolder': str(folder)}))
        (folder / prefs.name).write_bytes(plistlib.dumps({'EnableAPIServer': True}))
        self.assertTrue(support.iterm_preferences(self.home)['EnableAPIServer'])

    def test_alternate_config_locations_and_invalid_relative_locations(self):
        paths = installer.locations(self.home, ROOT, {'CODEX_HOME': str(self.home / 'codex custom'), 'XDG_CONFIG_HOME': str(self.home / 'config custom')})
        self.assertEqual(paths['config'], self.home / 'codex custom/config.toml')
        self.assertEqual(paths['settings'], self.home / 'config custom/codex-iterm2-status/settings.json')
        for environ in [{'CODEX_HOME': 'relative'}, {'XDG_CONFIG_HOME': 'relative'}]:
            with self.assertRaises(ValueError):
                installer.locations(self.home, ROOT, environ)

    def test_probe_timeout_never_leaks_child_output(self):
        with patch.object(diagnostics.subprocess, 'run', side_effect=subprocess.TimeoutExpired('private command', 10, output='secret')):
            self.assertIsNone(diagnostics.probe(['anything']))


class HookInterpreter(unittest.TestCase):
    def test_saved_interpreter_with_shell_characters_and_minimal_path(self):
        with tempfile.TemporaryDirectory(prefix="python O'Reilly ") as temp:
            folder = Path(temp)
            config = folder / 'codex-iterm2-status'
            config.mkdir()
            interpreter = folder / 'python $(unused)'
            interpreter.symlink_to(sys.executable)
            (config / 'python-path').write_text(str(interpreter) + '\n')
            env = dict(os.environ, XDG_CONFIG_HOME=str(folder), PLUGIN_ROOT=str(ROOT),
                       CODEX_ITERM2_PYTHON='', ITERM_SESSION_ID='', PATH='/bin')
            result = subprocess.run(['/bin/sh', str(ROOT/'scripts/hook.sh')], input='{}', text=True,
                                    capture_output=True, env=env, timeout=3)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '{}\n', ''))

    def test_missing_interpreter_is_observational(self):
        env = dict(os.environ, CODEX_ITERM2_PYTHON='/no/such/python', PLUGIN_ROOT=str(ROOT))
        result = subprocess.run(['/bin/sh', str(ROOT/'scripts/hook.sh')], input='{}', text=True,
                                capture_output=True, env=env, timeout=3)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '{}\n', ''))


if __name__ == '__main__':
    unittest.main()
