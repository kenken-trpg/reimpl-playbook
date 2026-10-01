#!/usr/bin/env python3
"""Watch a living external spec for the changes that break your reader.

The case this exists for: the subject reads something that is *not* in your
repository and *not* versioned - a published spreadsheet, a hosted schema, a
third-party export format, a vendor's API shape. It gets revised whenever
somebody finds something to fix, and a revision can move a cell, rename a
section, widen a block or add an enum value.

A test suite built on a fixture never sees any of that. The fixture is a copy
of the spec as it was the day it was taken, so the suite stays green while the
live document walks away from it, and the first report is a user whose import
silently lost half its data.

So this does what a test cannot: fetch what is live, reduce it to the handful
of facts the reader actually leans on, and diff those against a baseline
checked in beside it. Two design choices make it usable:

* **reduce before diffing.** A raw diff of a living document is noise. Pull
  out only the facts with code behind them - section names, enum entries,
  block extents, the labels sitting beside hard-coded addresses.
* **print the code that has to move.** Every watched fact carries the symbol
  that depends on it, so the output is a work list, not a diff.

    python tools/drift/watch.py            # check against the baseline
    python tools/drift/watch.py --json
    python tools/drift/watch.py --update   # adopt what is live now

`--update` is how a reviewed change is accepted: the baseline moves in the
same commit as the code that follows it, so the diff of that commit is the
record of what upstream did and what it cost.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

BASELINE = Path(__file__).with_name("baseline.json")

#: fact name -> (what reads it, how to extract it from the fetched spec)
#:
#: Replace the body with your own probes. The second element names the symbol
#: that has to change if the fact does - that string is the entire value of
#: this file over a plain diff.
Probe = tuple[str, Callable[[Any], Any]]
PROBES: dict[str, Probe] = {}


def fetch_spec() -> Any:
    """Return the live spec in whatever form the probes expect.

    Implement this per project: an HTTP GET, a spreadsheet export, a schema
    introspection call. It is the only part of this file that knows a URL.
    """
    raise NotImplementedError("implement fetch_spec() for your spec")


def observe() -> dict[str, Any]:
    spec = fetch_spec()
    return {name: probe(spec) for name, (_owner, probe) in PROBES.items()}


def diff(baseline: dict[str, Any], live: dict[str, Any]) -> list[str]:
    out = []
    for name in sorted(set(baseline) | set(live)):
        was, now = baseline.get(name), live.get(name)
        if was == now:
            continue
        owner = PROBES.get(name, ("(unknown)", None))[0]
        out.append(f"{name}  [{owner}]")
        out.append(f"    was: {json.dumps(was, ensure_ascii=False)}")
        out.append(f"    now: {json.dumps(now, ensure_ascii=False)}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)

    live = observe()
    if args.update:
        BASELINE.write_text(json.dumps(live, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"baseline updated: {BASELINE}")
        return 0
    if args.json:
        print(json.dumps(live, ensure_ascii=False, indent=2))
        return 0
    if not BASELINE.exists():
        print("no baseline yet — run with --update", file=sys.stderr)
        return 2
    changes = diff(json.loads(BASELINE.read_text(encoding="utf-8")), live)
    if not changes:
        print("spec unchanged in every watched fact")
        return 0
    print("the spec moved. each line names the code that has to move with it:\n")
    print("\n".join(changes))
    return 1


if __name__ == "__main__":
    sys.exit(main())
