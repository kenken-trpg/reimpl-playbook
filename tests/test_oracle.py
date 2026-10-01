"""The harness finds what it claims to find.

Each test breaks the example subject in one specific way and asserts that the
check meant to catch it does, and — just as important — that the others do
not. A harness whose checks all light up together cannot tell you anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from example import adapter
from tools.oracle import balance, compare_totals, fidelity, roundtrip

CORPUS = Path(__file__).resolve().parents[1] / "example" / "corpus"
FINAL = CORPUS / "a-1.xml"


def test_a_correct_subject_agrees_with_the_reference():
    row = balance(FINAL.read_bytes(), "a-1", adapter.oracle, adapter.subject)
    assert row.comparable and row.error is None
    assert row.off(adapter.TOLERANCES) == []


def test_a_draft_is_not_compared():
    row = balance((CORPUS / "draft-7.xml").read_bytes(), "d", adapter.oracle, adapter.subject)
    assert not row.comparable and row.totals == {}


def test_a_wrong_rule_shows_up_in_the_balance():
    """The cheapest check, and the one that needs no field mapping: forget the
    tax and the stated total disagrees."""

    class NoTax(adapter.InvoiceSubject):
        def compute(self, state):
            return {"total": sum(line.qty * line.unit for line in state.lines)}

    row = balance(FINAL.read_bytes(), "a-1", adapter.oracle, NoTax())
    assert row.off(adapter.TOLERANCES) == ["total"]


def test_a_tolerance_absorbs_rounding_but_not_a_rule():
    class OffByHalf(adapter.InvoiceSubject):
        def compute(self, state):
            return {"total": super().compute(state)["total"] + 0.5}

    row = balance(FINAL.read_bytes(), "a-1", adapter.oracle, OffByHalf())
    assert row.off(adapter.TOLERANCES) == []
    assert row.off({}) == ["total"]


def test_a_subject_that_crashes_is_reported_not_raised():
    """A run over a real corpus hits artefacts the subject cannot load yet. A
    harness that stops on the first one reports one problem per run."""

    class Broken(adapter.InvoiceSubject):
        def load(self, raw):
            raise ValueError("nope")

    row = balance(FINAL.read_bytes(), "a-1", adapter.oracle, Broken())
    assert row.error == "ValueError: nope"


def test_the_round_trip_catches_what_the_export_cannot_write():
    class LosesQuantity(adapter.InvoiceSubject):
        def export(self, state):
            raw = super().export(state)
            return raw.replace(b"<qty>2</qty>", b"<qty>1</qty>")

    changes = roundtrip(FINAL.read_bytes(), LosesQuantity())
    assert any("lost" in line for line in changes)
    assert any("gained" in line for line in changes)


def test_the_round_trip_also_watches_the_totals():
    """Holdings can survive a trip that still changes the answer."""

    class LosesTaxRate(adapter.InvoiceSubject):
        def export(self, state):
            return super().export(state).replace(b"<taxrate>0.1</taxrate>", b"<taxrate>0</taxrate>")

    assert compare_totals(FINAL.read_bytes(), LosesTaxRate()) == ["total: 3300 -> 3000"]


_DEFAULT = object()


def _fid(subject, drops=_DEFAULT, compare=adapter.COMPARE):
    # `drops or ACCEPTED_DROPS` would be wrong: `{}` is the case the last test
    # in this file is about, and it is falsy.
    if drops is _DEFAULT:
        drops = adapter.ACCEPTED_DROPS
    return fidelity(FINAL.read_bytes(), "a-1", adapter.oracle, subject, drops, compare)


def test_fidelity_is_clean_on_the_example():
    assert _fid(adapter.subject).clean


def test_fidelity_catches_a_field_the_round_trip_is_blind_to():
    """The whole reason both checks exist. Neither side reads `customer`, so
    dropping it round-trips cleanly and only the reference would notice."""

    class DropsCustomer(adapter.InvoiceSubject):
        def export(self, state):
            import re

            return re.sub(rb"<customer>[^<]*</customer>", b"", super().export(state))

    assert roundtrip(FINAL.read_bytes(), DropsCustomer()) == []
    assert _fid(DropsCustomer()).missing == ["customer"]


def test_a_changed_field_is_reported_separately_from_a_missing_one():
    class Renames(adapter.InvoiceSubject):
        def export(self, state):
            return super().export(state).replace(b"Acme Shipping", b"ACME SHIPPING")

    row = _fid(Renames())
    assert row.missing == []
    assert row.changed == [("customer", "Acme Shipping", "ACME SHIPPING")]


def test_an_accepted_drop_is_reported_with_its_reason_not_counted():
    row = _fid(adapter.subject)
    assert row.clean
    assert "printedat" in row.excused and row.excused["printedat"]


def test_an_unexcused_drop_fails_even_if_it_looks_harmless():
    """The asymmetry that keeps the list honest: anything not thought about
    yet fails, and an exemption costs one line and a sentence."""
    assert _fid(adapter.subject, drops={}).missing == ["printedat"]


@pytest.mark.parametrize("value", ["", "0", "False"])
def test_an_empty_value_the_reference_always_writes_is_not_a_field(value):
    row = fidelity(
        f"<invoice><mode>final</mode><note>{value}</note></invoice>".encode(),
        "x",
        adapter.oracle,
        adapter.subject,
        {},
        compare=None,
    )
    assert "note" not in row.missing
