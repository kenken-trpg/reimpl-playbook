"""A stale generated file fails, and the failure says how to fix it."""

from __future__ import annotations

from pathlib import Path

from tools.generated.check import main


def test_writing_creates_the_file(tmp_path, capsys):
    target = tmp_path / "out" / "types.ts"
    assert main(target, lambda: "export type A = 1;\n", argv=[]) == 0
    assert target.read_text() == "export type A = 1;\n"


def test_check_passes_when_the_tree_matches(tmp_path, capsys):
    target = tmp_path / "types.ts"
    target.write_text("export type A = 1;\n")
    assert main(target, lambda: "export type A = 1;\n", argv=["--check"]) == 0


def test_check_fails_with_a_diff_and_the_fix_command(tmp_path, capsys):
    target = tmp_path / "types.ts"
    target.write_text("export type A = 1;\n")
    code = main(target, lambda: "export type A = 2;\n", argv=["--check"], fix_command="make types")
    out, err = capsys.readouterr()
    assert code == 1
    assert "-export type A = 1;" in out and "+export type A = 2;" in out
    assert "make types" in err


def test_a_missing_file_is_stale_rather_than_a_crash(tmp_path):
    assert main(tmp_path / "nope.ts", lambda: "x\n", argv=["--check"]) == 1
