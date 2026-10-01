"""Resolve a merge conflict by keeping both sides, ours first.

For files where the two branches did not disagree so much as each add
something: a CHANGELOG entry, a test case. Anything else is a real conflict
and `merge_chain.sh` stops instead of calling this.
"""

from __future__ import annotations

import re
import sys

CONFLICT = re.compile(r"^<<<<<<< [^\n]*\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*\n", re.S | re.M)


def main() -> int:
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        merged = CONFLICT.sub(lambda m: m.group(1) + m.group(2), text)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(merged)
        print(f"{path} {text.count('<<<<<<<')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
