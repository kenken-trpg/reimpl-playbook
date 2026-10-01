"""The two sides the harness compares, and nothing about either one.

A reimplementation project has exactly two things to talk to: the artefacts
the **reference implementation** wrote, and the **subject** — the new code
being built. Everything in this package is written against these protocols so
that the harness itself carries no knowledge of the domain. Implement them in
your own repository (one module, usually under a hundred lines) and the whole
report below works.

The split matters more than it looks. `Oracle` reads the reference's own
output and is allowed to be dumb: a parser, not a model. The moment it starts
*computing* anything, the comparison is measuring the harness against itself
and will agree with the subject for the wrong reason.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Oracle(Protocol):
    """What the reference implementation's own file says, read literally."""

    def totals(self, raw: bytes) -> dict[str, float]:
        """The bottom-line numbers the artefact *states*.

        These are the gold: a field the reference wrote down as the result of
        its whole computation. One mismatch says "something differs" without
        having to know what, which is what makes it worth comparing first.

        Return only the numbers the artefact genuinely states. A number this
        method derives is not evidence.
        """

    def fields(self, raw: bytes) -> dict[str, str]:
        """A flat `path -> text` map of the artefact, for field-by-field work.

        Values are the literal text. Empty-ish values should be left out (see
        `fidelity.EMPTY_VALUES`) — the reference usually writes every field
        whether or not this artefact has one.
        """

    def is_comparable(self, raw: bytes) -> bool:
        """False for an artefact whose totals mean something else.

        There is always a mode where the stated total is a running balance, a
        partial save, a template. Comparing those reports differences that are
        not defects, which is how a report stops being read.
        """
        ...


@runtime_checkable
class Subject(Protocol):
    """The new implementation, reduced to import / compute / export."""

    def load(self, raw: bytes) -> Any:
        """The reference's artefact, as the subject's own state."""

    def compute(self, state: Any) -> dict[str, float]:
        """The same keys `Oracle.totals` returns, computed from scratch."""

    def export(self, state: Any) -> bytes:
        """The subject's state, written back in the reference's format."""

    def holdings(self, state: Any) -> Any:
        """A `collections.Counter` of what the state holds, identity aside.

        Whatever a lossy round trip would drop or duplicate: rows, line items,
        installed parts — with enough of each row in the key to tell two
        similar ones apart, and with generated ids left out, since those are
        new on every import.
        """
