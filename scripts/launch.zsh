#!/bin/zsh
# Launched by a login/interactive zsh so the user's normal Codex PATH is available.
# 2026-09-09
if [[ "$1" == "--workspace" ]]; then
  if [[ -z "$2" ]]; then
    print -u2 "Usage: launch.zsh --workspace DIRECTORY [Codex arguments]"
    exit 2
  fi
  cd -- "$2" || exit 1
  shift 2
fi
runtime_dir="${XDG_CONFIG_HOME:-$HOME/.config}/codex-iterm2-status"
exit_shell="${SHELL:-/bin/zsh}"
if [[ -r "$runtime_dir/shell-path" ]]; then
  IFS= read -r exit_shell < "$runtime_dir/shell-path"
fi
if [[ -r "$runtime_dir/search-path" ]]; then
  IFS= read -r install_path < "$runtime_dir/search-path"
  export PATH="$PATH:$install_path"
fi
export SHELL="$exit_shell"
codex_path=""
if [[ -r "$runtime_dir/codex-path" ]]; then
  IFS= read -r codex_path < "$runtime_dir/codex-path"
fi
if [[ ! -x "$codex_path" ]]; then
  codex_path=$(command -v codex)
fi
if [[ -z "$codex_path" ]]; then
  print -u2 "Codex CLI was not found in PATH. Install it or fix your shell PATH."
  exec "$exit_shell" -l
fi
# Codex can defer SessionStart until the first prompt; list this launcher now.
if [[ "$TERM_PROGRAM" == "iTerm.app" && -n "$ITERM_SESSION_ID" ]]; then
  printf '\e]21337;status=idle;indicator=#98c379;status-color=#98c379;detail=Codex\a'
fi
"$codex_path" "$@"
codex_exit_status=$?
# A normal session end is handled by the hook. This also clears after Ctrl-C or
# a CLI crash when the process exits but the terminal stays open.
if [[ "$TERM_PROGRAM" == "iTerm.app" && -n "$ITERM_SESSION_ID" ]]; then
  printf '\e]21337;status=;indicator=;status-color=;detail=\a'
fi
print "Codex exited ($codex_exit_status). This terminal is ready for shell commands."
exec "$exit_shell" -l
