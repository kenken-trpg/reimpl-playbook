#!/usr/bin/env bash
# Preflight for a fresh checkout. Non-fatal by design — it prints what to fix.
#
# A reimplementation project has an unusually long setup (an interpreter, a
# node toolchain, a container runtime, *and* a vendored copy of the reference's
# data at the right ref), and every one of them fails differently. Without this
# the first failure a newcomer sees is a test error three layers down.
#
# Non-fatal is the point: it should list everything wrong in one pass, not stop
# at the first. The exit code is there for CI, not for the person reading it.
cd "$(dirname "$0")/../.."
rc=0
good() { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[33m✗\033[0m %s\n' "$1"; rc=1; }

echo "toolchain:"
# `python3` is the POSIX spelling; the python.org installer for Windows only
# ships `python`.
PY=$(command -v python3 || command -v python) || true
if [ -n "$PY" ]; then
  v=$("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])')
  case "$v" in 3.1[1-9] | 3.[2-9][0-9]) good "python $v" ;; *) bad "python $v — need >= 3.11" ;; esac
else
  bad "python not found"
fi
[ -x .venv/bin/python ] || [ -x .venv/Scripts/python.exe ] \
  && good ".venv" || bad ".venv missing — run 'make setup'"

echo "the reference's data:"
if [ -f vendor/upstream/.upstream-ref ]; then
  good "vendored at $(cut -c1-12 vendor/upstream/.upstream-ref)"
else
  bad "vendor/upstream missing — run 'make data'"
fi
if [ -d vendor/upstream-corpus ] && [ -n "$(ls -A vendor/upstream-corpus 2>/dev/null)" ]; then
  good "corpus: $(ls vendor/upstream-corpus | wc -l | tr -d ' ') artefacts"
else
  bad "no corpus — run 'make corpus'; the oracle harness has nothing to measure without it"
fi

echo "tools:"
command -v gh >/dev/null 2>&1 && good "gh $(gh --version | head -1 | awk '{print $3}')" \
  || bad "gh not found — merge_chain.sh needs it"

exit $rc
