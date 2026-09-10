#!/usr/bin/env python3
"""Repository-owned validation, versioning, and reproducible source packaging."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / '.codex-plugin/plugin.json'
SEMVER = r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?'


def validate():
    manifest = json.loads(MANIFEST.read_text())
    if manifest.get('name') != 'iterm2-status' or not re.fullmatch(SEMVER, manifest.get('version', '')):
        raise ValueError('Manifest must have the plugin name and a semantic version.')
    if any(k in manifest for k in ['hooks', 'apps', 'mcpServers']):
        raise ValueError('Manifest must use the supported plugin schema.')
    hooks = json.loads((ROOT / 'hooks/hooks.json').read_text())['hooks']
    for groups in hooks.values():
        for group in groups:
            for hook in group['hooks']:
                if hook['type'] != 'command' or hook['command'] != '/bin/sh "${PLUGIN_ROOT}/scripts/hook.sh"' or not 1 <= hook['timeout'] <= 3:
                    raise ValueError('Unexpected hook entry; review plugin hook compatibility.')
    for path in ROOT.rglob('*.py'):
        if not any(part in {'.git', '.venv', 'dist', '__pycache__'} for part in path.relative_to(ROOT).parts):
            compile(path.read_bytes(), str(path.relative_to(ROOT)), 'exec')
    subprocess.run(['/bin/sh', '-n', str(ROOT / 'scripts/hook.sh')], check=True)
    subprocess.run(['/bin/zsh', '-n', str(ROOT / 'scripts/launch.zsh')], check=True)
    return manifest


def version(value=None, dev=False):
    manifest = validate()
    updated = value or manifest['version'].split('+', 1)[0]
    if dev:
        updated = updated.split('+', 1)[0] + '+codex.' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    if not re.fullmatch(SEMVER, updated):
        raise ValueError('Use a semantic version, for example 0.2.0-beta.1.')
    manifest['version'] = updated
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n')
    print('Version:', updated)


def package():
    manifest = validate()
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    if status.strip():
        raise ValueError('Commit source changes before packaging. The archive must match HEAD.')
    directory = ROOT / 'dist'
    directory.mkdir(exist_ok=True)
    archive = directory / ('iterm2-status-v' + manifest['version'].split('+', 1)[0] + '.zip')
    subprocess.run(['git', 'archive', '--format=zip', '--prefix=iterm2-status/', '--output=' + str(archive), 'HEAD'], cwd=ROOT, check=True)
    with zipfile.ZipFile(archive) as source:
        bad = source.testzip()
        if bad:
            raise ValueError('Invalid release archive: ' + bad)
        packed = json.loads(source.read('iterm2-status/.codex-plugin/plugin.json'))
        if packed != manifest:
            raise ValueError('Archive and source manifest differ.')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(digest + '  ' + archive.name + '\n')
    print(archive)
    print('SHA256:', digest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validate', 'version', 'package'])
    parser.add_argument('--set', dest='value')
    parser.add_argument('--dev', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'validate':
            validate()
            print('Manifest, hooks, Python and shell syntax validated.')
        elif args.command == 'version':
            version(args.value, args.dev)
        else:
            package()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('Error:', error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
