#!/usr/bin/env bash
# Run a command, retrying it a few times if it fails.
#
# For dependency installs only. Neither PyPI nor the npm registry is a
# guaranteed-available service, and when one of them serves an empty index page
# for a moment, pip reports it the same way it reports a real mistake:
#
#   ERROR: Could not find a version that satisfies the requirement
#          some-transitive-dep==2.46.5 (from somepkg) (from versions: none)
#
# "from versions: none" is the tell — not "this pin is unsatisfiable" but "the
# index returned nothing at all". It has turned CI red on a requirements file
# that had worked minutes earlier on the PR before it, and no version
# constraint could have prevented it: the wheels it could not see exist, for
# every interpreter in the matrix.
#
# So the answer is to ask again rather than to pin harder. Waiting between
# tries is the point — the gaps are seconds-to-minutes, so 15s and then 60s.
#
#   scripts/retry.sh pip install -r requirements-dev.txt
set -uo pipefail

DELAYS=(15 60)

for attempt in 0 1 2; do
  if [ "$attempt" -gt 0 ]; then
    delay=${DELAYS[$((attempt - 1))]}
    echo "retry.sh: attempt $((attempt + 1))/3 in ${delay}s — '$*' failed" >&2
    sleep "$delay"
  fi
  "$@" && exit 0
done

echo "retry.sh: '$*' failed three times; treating it as a real failure" >&2
exit 1
