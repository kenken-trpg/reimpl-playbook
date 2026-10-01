"""One artefact's bottom line: what the reference says against what we compute.

This is the cheapest high-signal check in a reimplementation and the one to
build first. It needs no field mapping and no knowledge of the rules: the
reference wrote down its own answer, so a difference is proof that an input,
a price or a rule differs — before anyone knows which.

Tolerances exist because a reference that keeps money as a decimal will
disagree in the last place for reasons that are not defects. Keep them as
tight as the format allows and name each one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .subject import Oracle, Subject


@dataclass(frozen=True)
class Balance:
    """One artefact's comparison, per total."""

    name: str
    comparable: bool
    #: key -> (reference, subject)
    totals: dict[str, tuple[float, float]] = field(default_factory=dict)
    #: what blew up, if the subject could not get through this artefact at all
    error: str | None = None

    def off(self, tolerances: dict[str, float]) -> list[str]:
        """The keys that differ by more than their tolerance."""
        return [
            key
            for key, (theirs, ours) in self.totals.items()
            if abs(theirs - ours) > tolerances.get(key, 0.0)
        ]


def balance(raw: bytes, name: str, oracle: Oracle, subject: Subject) -> Balance:
    """Compare one artefact. Never raises: a crash is a finding, not a stop.

    A reimplementation run over a real corpus hits artefacts it cannot load
    yet, and a harness that stops on the first one can only ever report one
    problem per run.
    """
    if not oracle.is_comparable(raw):
        return Balance(name=name, comparable=False)
    try:
        theirs = oracle.totals(raw)
        ours = subject.compute(subject.load(raw))
    except Exception as exc:  # noqa: BLE001 — the point is to keep going
        return Balance(name=name, comparable=True, error=f"{type(exc).__name__}: {exc}")
    return Balance(
        name=name,
        comparable=True,
        totals={key: (value, float(ours.get(key, 0.0))) for key, value in theirs.items()},
    )
