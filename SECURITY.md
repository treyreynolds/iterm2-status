# Privacy and security

This plugin is observational. It receives Codex hook events, derives a status, and
calls the local iTerm utility with an explicit session UUID. It does not make tool
or approval decisions, read chat transcripts, run model requests, or send telemetry.
It does not change Codex's model, sandbox, or approval policy.

The status cache stores IDs, project basenames, event/status metadata, timestamps,
and tool-identity hashes. A hash is not encryption; predictable tool identities
can be guessed. Raw prompts, tool commands, and tool output are not saved. Cache
files and local backups use private file permissions. Local status tombstones are
retained to reject late events.

`doctor --json` exposes only versions and named check results. It excludes personal
paths, terminal/project identities, hook payloads, and child-process output. Full
configuration files and backups may contain sensitive settings; never post them.

Only the latest beta is maintained during the beta period. Security reports should
use [GitHub's private vulnerability reporting](https://github.com/treyreynolds/iterm2-status/security/advisories/new).
Do not disclose credentials or an exploitable vulnerability in a public issue.
This is a community project with no guaranteed response-time service agreement.
