"""The coverage number is derived, and the dispatch table cannot be ambiguous."""

from __future__ import annotations

import pytest

from tools.coverage import registry


@pytest.fixture(autouse=True)
def clean_registry():
    saved, silent = dict(registry._HANDLERS), set(registry.SILENT)
    registry._HANDLERS.clear()
    registry.SILENT.clear()
    yield
    registry._HANDLERS.update(saved)
    registry.SILENT.update(silent)


def test_a_handler_registers_itself_and_nothing_else_has_to():
    @registry.handles("dodge")
    def _dodge():
        return 1

    assert registry.implemented() == {"dodge"}
    assert registry.handler("dodge") is _dodge


def test_one_function_can_claim_several_tags():
    @registry.handles("a", "b")
    def _both():
        return 1

    assert registry.implemented() == {"a", "b"}


def test_two_modules_claiming_one_tag_raise_at_import():
    """The one failure mode a dispatch table has, made loud."""

    @registry.handles("clash")
    def _first():
        return 1

    with pytest.raises(RuntimeError, match="claimed by both"):

        @registry.handles("clash")
        def _second():
            return 2


def test_unimplemented_is_ranked_by_how_often_the_data_uses_it():
    @registry.handles("known")
    def _known():
        return 1

    registry.SILENT.add("ignored")
    missing = registry.unimplemented(["known", "ignored", "rare", "common", "common", "common"])
    assert missing.most_common() == [("common", 3), ("rare", 1)]


def test_coverage_counts_the_three_states_apart():
    @registry.handles("known")
    def _known():
        return 1

    registry.SILENT.add("ignored")
    out = registry.coverage(["known", "known", "ignored", "todo", "todo"])
    assert out["tags_in_data"] == 3
    assert (out["handled"], out["silent"], out["unimplemented"]) == (1, 1, 1)
    # distinct tags missing vs. how much of the data they cover: different numbers
    assert out["uses_unhandled"] == 2
