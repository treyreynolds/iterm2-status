#!/usr/bin/env python3
"""Fresh-runner integration test using real, checksum-verified upstream binaries.

Refuses to run on a normal workstation. No Codex account or model call is needed.
This tests installation and cache/profile behavior; it does not claim GUI or
approval-event coverage. Those require the separate live smoke checklist.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile

CODEX_VERSION = '0.153.4'
CODEX_DIGESTS = {
    'arm64': ('aarch64', '8cf911ea676523bfb2121ec561848d2aba564890ad536db4d8a3353f2b9850b1'),
    'x86_64': ('x86_64', 'd69200f0bf841b1d1a07f80b80cf742a2e4fc2bab91ae8a44b1042f8e8ca9fa4'),
}
ITERM_DIGEST = '14b5131e9134d0012466574fba6d69fb9ef84eee66660ee861e2da483089574a'


def download(url, path, expected):
    # Use macOS's standard downloader and trust store, as for a manual download.
    subprocess.run(['/usr/bin/curl', '--fail', '--location', '--silent', '--show-error',
                    '--retry', '3', '--max-time', '90', '--output', str(path), url],
                   check=True, timeout=120)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Upstream archive checksum mismatch: ' + path.name)


def run(command, **kwargs):
    return subprocess.run([str(arg) for arg in command], check=True, text=True, timeout=60, **kwargs)


def installed(codex):
    output = run([codex, 'plugin', 'list', '--marketplace', 'personal', '--json'], capture_output=True)
    return [p for p in json.loads(output.stdout)['installed'] if p['name'] == 'iterm2-status']


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or sys.platform != 'darwin':
        raise RuntimeError('This integration test runs only on a fresh GitHub macOS runner.')
    canonical = Path.home() / 'plugins/iterm2-status'
    marketplace = Path.home() / '.agents/plugins/marketplace.json'
    if canonical.exists() or canonical.is_symlink() or marketplace.exists():
        raise RuntimeError('Expected a fresh runner without an existing personal plugin installation.')
    with tempfile.TemporaryDirectory(prefix="Codex O'Reilly ") as temporary:
        folder = Path(temporary)
        architecture, digest = CODEX_DIGESTS[platform.machine()]
        archive = folder / 'codex.tar.gz'
        member_name = 'codex-' + architecture + '-apple-darwin'
        download('https://github.com/openai/codex/releases/download/rust-v' + CODEX_VERSION + '/' + member_name + '.tar.gz', archive, digest)
        codex = folder / 'codex cli'
        with tarfile.open(archive) as source:
            member = source.getmember(member_name)
            if not member.isfile():
                raise RuntimeError('Expected a regular Codex binary.')
            with source.extractfile(member) as stream, codex.open('wb') as output:
                shutil.copyfileobj(stream, output)
        codex.chmod(0o700)
        iterm_zip = folder / 'iterm.zip'
        download('https://iterm2.com/downloads/stable/iTerm2-3_7_0.zip', iterm_zip, ITERM_DIGEST)
        apps = folder / 'Custom Applications'
        run(['/usr/bin/ditto', '-x', '-k', iterm_zip, apps])
        app = apps / 'iTerm.app'
        source = folder / "source with spaces $(literal)" / 'iterm2-status'
        shutil.copytree(Path(__file__).resolve().parents[1], source,
                        ignore=shutil.ignore_patterns('.git', 'dist', '__pycache__', '*.pyc'))
        installer = source / 'install.py'
        manifest = source / '.codex-plugin/plugin.json'
        original_manifest = manifest.read_text()
        original_version = json.loads(original_manifest)['version']
        run([sys.executable, installer, '--codex', codex, '--iterm-app', app,
             '--workspace', source, '--workspace-name', 'Codex — Unicode workspace'])
        assert installed(codex)[0]['version'] == original_version
        assert installed(codex)[0]['enabled']
        original_marketplace = marketplace.read_bytes()
        profiles = Path.home() / 'Library/Application Support/iTerm2/DynamicProfiles/codex-profiles.json'
        original_profiles = profiles.read_bytes()
        run([sys.executable, installer])
        assert marketplace.read_bytes() == original_marketplace
        assert profiles.read_bytes() == original_profiles
        report = subprocess.run([sys.executable, str(installer), 'doctor', '--json'], capture_output=True,
                                text=True, timeout=60)
        checks = json.loads(report.stdout)['checks']
        # Headless CI has no running/authorized iTerm UI. Everything else must
        # pass against the actual Codex cache and dynamic profiles.
        errors = [c['id'] for c in checks if c['status'] == 'error']
        assert set(errors) <= {'iterm_api'}, errors
        run([sys.executable, source / 'tools/dev.py', 'version', '--dev'])
        updated_version = json.loads(manifest.read_text())['version']
        assert updated_version != original_version
        run([sys.executable, installer])
        assert installed(codex)[0]['version'] == updated_version
        manifest.write_text(original_manifest)
        run([sys.executable, installer])
        assert installed(codex)[0]['version'] == original_version
        custom = {'Name': 'Unrelated profile', 'Guid': 'unrelated-ci-profile'}
        content = json.loads(profiles.read_text())
        content['Profiles'].append(custom)
        profiles.write_text(json.dumps(content))
        run([sys.executable, installer, 'uninstall'])
        assert not installed(codex)
        assert json.loads(profiles.read_text())['Profiles'] == [custom]
        run([sys.executable, installer, 'uninstall'])
        assert json.loads(profiles.read_text())['Profiles'] == [custom]
        assert marketplace.read_bytes() == original_marketplace
        print('PASS: real CLI install, repeat install, upgrade, rollback, diagnostics, and repeat uninstall.')
        print('Verified architecture:', platform.machine(), 'macOS:', platform.mac_ver()[0])


if __name__ == '__main__':
    main()
