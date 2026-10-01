"""The export against the artefact the reference wrote, field by field.

This answers the question `roundtrip` cannot. Reading our own export with our
own importer is blind to anything the reference needs and we do not: a field
neither side reads comes back unchanged because neither side looked.

The reference is the *other* reader of these files, and the only statement of
what it expects is the artefact it wrote. So this compares the original
against the export over the fields the reference states — and it is a gate,
not a reading to work down: a field both sides state with different text
fails, and so does one the original states that the export drops. A field the
reference writes and never reads back (a cached total, a timestamp) is named
in `accepted_drops` *with its reason* and reported instead of counted.

That asymmetry is the design. Anything not yet thought about fails, which is
what keeps the list honest as the subject grows; an exemption costs one line
and a sentence, which is cheap enough to be written and expensive enough not
to be written casually.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .subject import Oracle, Subject

#: A value the reference wrote that says nothing: the element is there because
#: it writes every field, not because this artefact has one.
EMPTY_VALUES = {"", "0", "0.0", "false", "False", "null", "None"}


@dataclass(frozen=True)
class Fidelity:
    name: str
    #: fields the original states, the export does not, and nothing excuses
    missing: list[str] = field(default_factory=list)
    #: (path, theirs, ours) — both state it, with different text
    changed: list[tuple[str, str, str]] = field(default_factory=list)
    #: path -> reason, dropped on purpose
    excused: dict[str, str] = field(default_factory=dict)

    @property
    def clean(self) -> bool:
        return not self.missing and not self.changed


def fidelity(
    raw: bytes,
    name: str,
    oracle: Oracle,
    subject: Subject,
    accepted_drops: dict[str, str],
    compare: tuple[str, ...] | None = None,
) -> Fidelity:
    """Compare the original and the subject's export over the reference's fields.

    `compare` narrows the check to the paths worth comparing by value — in
    practice the artefact's own header, plus whatever the reference keeps
    exactly one of. Everything else is usually a list the subject rebuilds
    from its own catalogue, which is *supposed* to differ. Left as None, every
    field the original states is compared, which is the right place to start
    and usually too noisy to keep.
    """
    theirs = {k: v for k, v in oracle.fields(raw).items() if v not in EMPTY_VALUES}
    ours = oracle.fields(subject.export(subject.load(raw)))
    if compare is not None:
        theirs = {k: v for k, v in theirs.items() if k in compare}
    missing, changed, excused = [], [], {}
    for path, value in sorted(theirs.items()):
        mine = ours.get(path)
        if mine is None or mine in EMPTY_VALUES:
            reason = accepted_drops.get(path)
            if reason is None:
                missing.append(path)
            else:
                excused[path] = reason
        elif mine != value:
            changed.append((path, value, mine))
    return Fidelity(name=name, missing=missing, changed=changed, excused=excused)
