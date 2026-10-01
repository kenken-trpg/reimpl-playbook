"""Everything the harness prints.

The modules beside this one answer questions and hand back data; this is the
only one that writes to a terminal. Keeping it that way is what lets the same
checks be a CI gate, a JSON artefact and a table a human reads down.

The table is the deliverable. A reimplementation lives or dies on whether
somebody looks at this output every week, so it is one line per artefact,
widest signal first, and it ends with counts — because the only number anyone
remembers is "how many agree today".
"""

from __future__ import annotations

import collections

from .balance import Balance
from .fidelity import Fidelity


def balance_table(rows: list[Balance], tolerances: dict[str, float]) -> str:
    keys: list[str] = []
    for row in rows:
        for key in row.totals:
            if key not in keys:
                keys.append(key)
    width = max([len(row.name) for row in rows] + [8])
    out = [f"{'artefact':<{width}}  " + "  ".join(f"{key}: ref / ours".ljust(28) for key in keys)]
    agree: collections.Counter[str] = collections.Counter()
    skipped = errors = 0
    for row in rows:
        if not row.comparable:
            skipped += 1
            out.append(f"{row.name:<{width}}  (not comparable)")
            continue
        if row.error:
            errors += 1
            out.append(f"{row.name:<{width}}  !! {row.error}")
            continue
        off = set(row.off(tolerances))
        cells = []
        for key in keys:
            theirs, ours = row.totals.get(key, (0.0, 0.0))
            delta = ours - theirs
            cells.append(f"{_num(theirs)} / {_num(ours)} ({delta:+g})".ljust(28))
            if key not in off:
                agree[key] += 1
        out.append(f"{row.name:<{width}}  " + "  ".join(cells) + ("  !=" if off else ""))
    comparable = sum(1 for row in rows if row.comparable and not row.error)
    out.append("")
    out.append(
        f"comparable: {comparable}  not comparable: {skipped}  failed to load: {errors}"
    )
    for key in keys:
        out.append(f"  {key} agrees: {agree[key]} of {comparable}")
    return "\n".join(out)


def _num(value: float) -> str:
    return f"{value:g}"


def fidelity_report(rows: list[Fidelity]) -> str:
    missing: collections.Counter[str] = collections.Counter()
    changed: collections.Counter[tuple[str, str, str]] = collections.Counter()
    excused: collections.Counter[str] = collections.Counter()
    reasons: dict[str, str] = {}
    for row in rows:
        missing.update(row.missing)
        changed.update(row.changed)
        # `.excused` is path -> reason, so count the keys; feeding the mapping
        # itself to a Counter would add the reasons as if they were counts.
        excused.update(row.excused.keys())
        reasons.update(row.excused)
    clean = sum(1 for row in rows if row.clean)
    out = [f"export fidelity: {clean} of {len(rows)} artefacts come back complete"]
    if missing:
        out.append("\nmissing - the reference states it, reads it back, and our export drops it:")
        out += [f"  {count:>4}  {path}" for path, count in missing.most_common()]
    if changed:
        out.append("\nchanged - both state it, with different text:")
        out += [
            f"  {count:>4}  {path}: {theirs!r} -> {ours!r}"
            for (path, theirs, ours), count in changed.most_common()
        ]
    if excused:
        out.append(f"\ndropped on purpose ({len(excused)} fields):")
        out += [
            f"  {count:>4}  {path} — {reasons[path]}" for path, count in excused.most_common()
        ]
    return "\n".join(out)
