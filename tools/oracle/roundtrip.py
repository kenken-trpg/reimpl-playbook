"""Export and read back: what the trip lost or gained.

Cheap, and it catches a real class of bug — something the import reads that
the export has nowhere to write. What it is blind to, by construction, is a
field *neither* side reads: it comes back unchanged because nobody looked,
and the trip calls that a pass. That blind spot is `fidelity`'s whole job, and
the two are not substitutes for each other.
"""

from __future__ import annotations

from typing import Any

from .subject import Subject


def roundtrip(raw: bytes, subject: Subject) -> list[str]:
    """What changed when the artefact was exported and imported again."""
    first = subject.load(raw)
    again = subject.load(subject.export(first))
    before, after = subject.holdings(first), subject.holdings(again)
    out = [f"lost {key} x{count}" for key, count in (before - after).items()]
    out += [f"gained {key} x{count}" for key, count in (after - before).items()]
    return out


def compare_totals(raw: bytes, subject: Subject) -> list[str]:
    """The computed totals before and after the trip, which must agree.

    Holdings can survive a trip that still changes the answer — a rating, a
    grade, a flag that only shows up in the arithmetic.
    """
    first: Any = subject.load(raw)
    again: Any = subject.load(subject.export(first))
    one, two = subject.compute(first), subject.compute(again)
    return [
        f"{key}: {one.get(key)} -> {two.get(key)}"
        for key in sorted(set(one) | set(two))
        if one.get(key) != two.get(key)
    ]
