"""How much of the reference's vocabulary the subject actually handles.

Every reimplementation of a rules-heavy program ends up with the same shape:
the reference expresses behaviour as tagged nodes in its data (`<bonus>`
children, effect codes, modifier keys), there are hundreds of distinct tags,
and the subject implements them a handful at a time.

The temptation is a hand-written table of "implemented tags". Do not: it
drifts the day somebody adds a handler and forgets the table, and after that
the one number the project is judged on is wrong in the optimistic direction.

Read it off the handler table instead. `@handles` *is* the registration, so a
tag is implemented exactly when a function claims it, and the coverage report
is derived rather than maintained. Two things fall out for free:

* a tag two modules both claim raises at import, which is the one failure mode
  a dispatch table has;
* `unimplemented(seen)` turns a run over the real corpus into the work list -
  ranked by how often the data actually uses each tag, which is a different
  order from how interesting they look.

`SILENT` is the other half. "Recognised and deliberately ignored" is a real
state (presentation-only tags, things that do not apply to the subject's
scope), and without somewhere to put it either the report cries wolf forever
or somebody writes an empty handler, which is a lie.
"""

from __future__ import annotations

import collections
from typing import Any, Callable, Iterable

Handler = Callable[..., Any]

_HANDLERS: dict[str, Handler] = {}

#: Tags recognised on purpose and doing nothing. Keep a reason beside each one
#: in your own module - a bare set rots into "nobody remembers why".
SILENT: set[str] = set()


def handles(*tags: str) -> Callable[[Handler], Handler]:
    """Register `func` as the handler for `tags`. The whole registration."""

    def decorate(func: Handler) -> Handler:
        for tag in tags:
            if tag in _HANDLERS:
                raise RuntimeError(
                    f"tag {tag!r} is claimed by both {_HANDLERS[tag].__qualname__} "
                    f"and {func.__qualname__}"
                )
            _HANDLERS[tag] = func
        return func

    return decorate


def implemented() -> frozenset[str]:
    return frozenset(_HANDLERS)


def handler(tag: str) -> Handler | None:
    return _HANDLERS.get(tag)


def unimplemented(seen: Iterable[str]) -> collections.Counter[str]:
    """Tags the data uses that nothing claims, counted by how often.

    Feed it every tag encountered in a run over the corpus. The counts are the
    priority order: a tag on one obscure item is not the same work as one on
    forty.
    """
    counts: collections.Counter[str] = collections.Counter()
    for tag in seen:
        if tag not in _HANDLERS and tag not in SILENT:
            counts[tag] += 1
    return counts


def coverage(seen: Iterable[str]) -> dict[str, Any]:
    """One dict to print or assert on: the number the project is judged by."""
    seen = list(seen)
    distinct = set(seen)
    missing = unimplemented(seen)
    handled = distinct - set(missing) - SILENT
    return {
        "tags_in_data": len(distinct),
        "handled": len(handled),
        "silent": len(distinct & SILENT),
        "unimplemented": len(missing),
        "uses_unhandled": sum(missing.values()),
        "worst": missing.most_common(20),
    }
