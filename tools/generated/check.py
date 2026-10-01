#!/usr/bin/env python3
"""Generate a file, or fail because the one in the tree is stale.

The problem this solves is specific and extremely common in a reimplementation:
the same shape ends up described twice, on two sides of a boundary. The state
crossing the wire is a Pydantic model *and* a TypeScript interface; the
database row is a dataclass *and* a migration; the enum is in the reference's
data *and* in your switch statement. The two drift, quietly, and the drift
shows up as a field that silently never reaches the other side.

The fix is never "be careful". It is to make one side generated from the other
and to have CI refuse a tree where the generated half is stale. Then the
duplicate still exists — it has to, the other language needs it — but it can
no longer disagree.

Two rules make this work in practice:

* **check the content, not a timestamp.** `--check` regenerates into memory
  and compares, so it is correct after a rebase, a checkout or a cache hit.
* **print the command to fix it.** A stale-file failure in CI is read by
  somebody who did not write the generator.

Wire your own generator in as a function returning the file's full text:

    from tools.generated.check import main
    main(target=Path("frontend/lib/types/state.ts"), render=render_typescript)
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path
from typing import Callable


def main(
    target: Path,
    render: Callable[[], str],
    argv: list[str] | None = None,
    fix_command: str | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=f"generate {target}")
    parser.add_argument("--check", action="store_true", help="fail if stale (CI)")
    args = parser.parse_args(argv)

    fresh = render()
    if not args.check:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(fresh, encoding="utf-8")
        print(f"wrote {target}")
        return 0

    current = target.read_text(encoding="utf-8") if target.exists() else ""
    if current == fresh:
        print(f"{target} is up to date")
        return 0
    sys.stdout.writelines(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            fresh.splitlines(keepends=True),
            fromfile=f"{target} (in the tree)",
            tofile=f"{target} (generated now)",
        )
    )
    print(
        f"\n{target} is stale. Run `{fix_command or 'the generator without --check'}` "
        "and commit the result.",
        file=sys.stderr,
    )
    return 1
