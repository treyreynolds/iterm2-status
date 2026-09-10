#!/bin/sh
# Keep interpreter selection out of the shared plugin manifest. Never source a
# settings file as shell code: paths may contain spaces, quotes, or shell syntax.
runtime_dir="${XDG_CONFIG_HOME:-$HOME/.config}/codex-iterm2-status"
python_path="${CODEX_ITERM2_PYTHON:-}"
if [ -z "$python_path" ] && [ -r "$runtime_dir/python-path" ]; then
  IFS= read -r python_path < "$runtime_dir/python-path"
fi
if [ -z "$python_path" ]; then
  python_path=$(command -v python3 2>/dev/null)
fi
if [ -n "$python_path" ] && [ -x "$python_path" ] && [ -f "${PLUGIN_ROOT:-}/scripts/status.py" ]; then
  "$python_path" -B "$PLUGIN_ROOT/scripts/status.py" 2>/dev/null || printf '{}\n'
else
  printf '{}\n'
fi
