"""A harness that measures a reimplementation against the thing it replaces.

Four checks, each answering a question the others cannot:

* `balance`   - the bottom line the reference wrote down, against ours.
* `roundtrip` - export and read back: what our own importer loses.
* `fidelity`  - our export against the reference's, field by field: what the
                *other* reader needs and we drop.
* `report`    - the table, which is the only part a human reads.

Wire it to your project by implementing `subject.Oracle` and
`subject.Subject` in an adapter module, and run `python -m tools.oracle.cli
--adapter your.module`.
"""

from .balance import Balance, balance
from .fidelity import Fidelity, fidelity
from .report import balance_table, fidelity_report
from .roundtrip import compare_totals, roundtrip

__all__ = [
    "Balance",
    "Fidelity",
    "balance",
    "balance_table",
    "compare_totals",
    "fidelity",
    "fidelity_report",
    "roundtrip",
]
