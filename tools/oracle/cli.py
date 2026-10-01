#!/usr/bin/env python3
"""Run the harness over a corpus of the reference's own artefacts.

    python -m tools.oracle.cli --adapter example.adapter --corpus vendor/upstream-corpus
    python -m tools.oracle.cli --adapter example.adapter --only fidelity --gate

The adapter module supplies:

    oracle          an object implementing tools.oracle.subject.Oracle
    subject         an object implementing tools.oracle.subject.Subject
    TOLERANCES      {total key: how much disagreement is rounding}
    ACCEPTED_DROPS  {field path: why our export may omit it}
    COMPARE         the field paths fidelity compares, or None for all
    GLOB            which files in the corpus directory are artefacts

`--gate` is what CI runs: it exits non-zero on a fidelity gap or a round-trip
loss, and *not* on a balance difference. That asymmetry is deliberate. Balance
is a reading that starts out mostly red and is worked down over months — gate
on it and the gate is just always failing. Fidelity and the round trip start
clean and must stay clean, so they are the ones worth blocking a merge.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from .balance import balance
from .fidelity import fidelity
from .report import balance_table, fidelity_report
from .roundtrip import compare_totals, roundtrip

CHECKS = ("balance", "roundtrip", "fidelity")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True, help="module supplying oracle/subject")
    parser.add_argument("--corpus", default="vendor/upstream-corpus", type=Path)
    parser.add_argument("--only", choices=CHECKS, action="append", default=None)
    parser.add_argument("--gate", action="store_true", help="exit non-zero on a regression")
    args = parser.parse_args(argv)

    mod = importlib.import_module(args.adapter)
    checks = args.only or list(CHECKS)
    files = sorted(args.corpus.glob(getattr(mod, "GLOB", "*")))
    if not files:
        print(f"no artefacts in {args.corpus} — fetch the corpus first", file=sys.stderr)
        return 2

    failed = False
    if "balance" in checks:
        rows = [balance(path.read_bytes(), path.name, mod.oracle, mod.subject) for path in files]
        print(balance_table(rows, mod.TOLERANCES))
        # A crash is a defect even though a difference is not.
        failed |= any(row.error for row in rows)

    if "roundtrip" in checks:
        print("\nround trip:")
        lost = 0
        for path in files:
            raw = path.read_bytes()
            changes = roundtrip(raw, mod.subject) + compare_totals(raw, mod.subject)
            if changes:
                lost += 1
                print(f"  {path.name}")
                print("\n".join(f"    {line}" for line in changes))
        print(f"  {len(files) - lost} of {len(files)} unchanged")
        failed |= lost > 0

    if "fidelity" in checks:
        print()
        rows = [
            fidelity(
                path.read_bytes(),
                path.name,
                mod.oracle,
                mod.subject,
                mod.ACCEPTED_DROPS,
                getattr(mod, "COMPARE", None),
            )
            for path in files
        ]
        print(fidelity_report(rows))
        failed |= any(not row.clean for row in rows)

    return 1 if (failed and args.gate) else 0


if __name__ == "__main__":
    sys.exit(main())
