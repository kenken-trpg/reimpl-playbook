"""A worked example of wiring `tools.oracle` to a project, end to end.

The domain is deliberately tiny — a reference program that writes invoices as
XML, and a subject that recomputes the total from the line items — because the
point is the *shape*, not the rules. Everything here has a counterpart in a
real project:

| here                        | a real project                          |
| --------------------------- | --------------------------------------- |
| `InvoiceOracle.totals`      | the bottom line the reference stated    |
| `is_comparable`             | drafts / career mode / partial saves    |
| `ACCEPTED_DROPS`            | fields the reference writes, never reads|
| `COMPARE`                   | the artefact header, not its lists      |
| `TOLERANCES`                | decimal money, float rounding           |

Run it:

    python -m tools.oracle.cli --adapter example.adapter --corpus example/corpus
"""

from __future__ import annotations

import collections
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

#: Money rounds; a yen is the smallest thing worth reporting.
TOLERANCES = {"total": 1.0}

#: Fields the reference writes and never reads back. Each needs a reason, and
#: the reason is the whole value of the entry: "it is fine" is not one.
ACCEPTED_DROPS = {
    "printedat": "a timestamp of the print run, not of the invoice; "
    "the reference stamps it fresh every time it writes one",
}

#: The invoice's own header — `printedat` included, so that the drop above is
#: *reported* rather than silently out of scope. Everything under `items/` is a
#: list the subject
#: rebuilds from its own catalogue, which is *supposed* to differ in order and
#: formatting — `roundtrip` covers that, by value.
COMPARE = ("id", "mode", "customer", "currency", "taxrate", "total", "printedat")

GLOB = "*.xml"


def _flatten(node: ET.Element, prefix: str = "") -> dict[str, str]:
    """`path -> text`, with repeated children indexed.

    Indexing by position is right for a list the reference writes in a fixed
    order and wrong for one it does not; if yours is unordered, key on the
    row's own identifier instead or the report fills with phantom changes.
    """
    out: dict[str, str] = {}
    counts: collections.Counter[str] = collections.Counter()
    for child in node:
        counts[child.tag] += 1
        same = sum(1 for other in node if other.tag == child.tag)
        name = f"{child.tag}[{counts[child.tag]}]" if same > 1 else child.tag
        path = f"{prefix}{name}"
        if len(child):
            out.update(_flatten(child, f"{path}/"))
        else:
            out[path] = (child.text or "").strip()
    return out


class InvoiceOracle:
    """Reads what the reference wrote. Computes nothing — see `subject.Oracle`."""

    def totals(self, raw: bytes) -> dict[str, float]:
        root = ET.fromstring(raw)
        return {"total": float(root.findtext("total") or 0)}

    def fields(self, raw: bytes) -> dict[str, str]:
        return _flatten(ET.fromstring(raw))

    def is_comparable(self, raw: bytes) -> bool:
        # A draft states a total of 0 because nobody has finalised it. Comparing
        # drafts would report every one of them as a difference, which is how a
        # report stops being read.
        return (ET.fromstring(raw).findtext("mode") or "").strip() == "final"


@dataclass
class Line:
    sku: str
    qty: int
    unit: float


@dataclass
class Invoice:
    id: str
    mode: str
    customer: str
    currency: str
    taxrate: float
    lines: list[Line] = field(default_factory=list)


class InvoiceSubject:
    """The new implementation: load, compute from scratch, write back."""

    def load(self, raw: bytes) -> Invoice:
        root = ET.fromstring(raw)
        return Invoice(
            id=root.findtext("id") or "",
            mode=root.findtext("mode") or "",
            customer=root.findtext("customer") or "",
            currency=root.findtext("currency") or "",
            taxrate=float(root.findtext("taxrate") or 0),
            lines=[
                Line(
                    sku=item.findtext("sku") or "",
                    qty=int(item.findtext("qty") or 0),
                    unit=float(item.findtext("unit") or 0),
                )
                for item in root.iterfind("items/item")
            ],
        )

    def compute(self, state: Invoice) -> dict[str, float]:
        net = sum(line.qty * line.unit for line in state.lines)
        return {"total": round(net * (1 + state.taxrate))}

    def export(self, state: Invoice) -> bytes:
        total = self.compute(state)["total"]
        items = "".join(
            f"<item><sku>{line.sku}</sku><qty>{line.qty}</qty>"
            f"<unit>{line.unit:g}</unit></item>"
            for line in state.lines
        )
        return (
            "<invoice>"
            f"<id>{state.id}</id><mode>{state.mode}</mode>"
            f"<customer>{state.customer}</customer><currency>{state.currency}</currency>"
            f"<taxrate>{state.taxrate:g}</taxrate><total>{total:g}</total>"
            f"<items>{items}</items>"
            "</invoice>"
        ).encode()

    def holdings(self, state: Invoice) -> Any:
        held: collections.Counter[tuple[Any, ...]] = collections.Counter()
        for line in state.lines:
            held[(line.sku, line.qty, line.unit)] += 1
        return held


oracle = InvoiceOracle()
subject = InvoiceSubject()
