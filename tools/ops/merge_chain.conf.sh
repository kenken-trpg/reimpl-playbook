# What `merge_chain.sh` needs to know about this repository. Edit, don't fork.

# The halves of the tree that can be checked independently. For each name there
# must be a `HALF_<name>_PATH` prefix and a `check_<name>` function.
HALVES="subject tools"

HALF_subject_PATH="src/"
HALF_tools_PATH="tools/"

# Each check must be what CI runs, as nearly as a laptop can manage. A local
# check that is *weaker* than CI is worse than none: it moves the discovery of
# a failure to after the merge, which is the one place this script exists to
# keep clear.
check_subject() {
  python -m pytest -q 2>&1 | tail -1
}

check_tools() {
  python -m pytest -q tests 2>&1 | tail -1
}

# A conflict in one of these is resolved by keeping both sides. A `case` glob
# list — keep it short, and keep anything whose duplicate would not be caught
# by a test out of it.
KEEP_BOTH='changelog.d/*|*/tests/*|*_test.py'

# Paths that cannot change what any check does: prose, CI config, changelog
# fragments. Anything NOT matching this and not under a half's prefix makes the
# run check every half.
PROSE='^(src/|tools/|tests/|changelog\.d/|docs/|\.github/|$)|\.md$'
