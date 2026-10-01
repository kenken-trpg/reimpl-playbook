"""The conflict resolver keeps both sides, in order, and leaves no markers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "ops" / "keep_both_sides.py"

CONFLICTED = """# Changelog
<<<<<<< HEAD
- ours
=======
- theirs
>>>>>>> feat/other
"""


def test_both_sides_survive_ours_first(tmp_path):
    target = tmp_path / "CHANGELOG.md"
    target.write_text(CONFLICTED, encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT), str(target)], check=True, capture_output=True)
    assert target.read_text(encoding="utf-8") == "# Changelog\n- ours\n- theirs\n"


def test_a_file_with_no_conflict_is_left_alone(tmp_path):
    target = tmp_path / "plain.md"
    target.write_text("nothing here\n", encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT), str(target)], check=True, capture_output=True)
    assert target.read_text(encoding="utf-8") == "nothing here\n"
