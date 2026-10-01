"""CHANGELOG fragments: one file per PR, folded into CHANGELOG.md at release.

Every PR used to add its entry right under `## [Unreleased]`, so any two open
PRs edited the same lines and the second one always conflicted. Now a PR adds
`changelog.d/<name>.<type>.md` instead — a file nobody else touches — and
`make changelog` moves them all into `[Unreleased]` when it is time to cut a
release.

    python tools/ops/changelog.py collect         # fold fragments in, delete them
    python tools/ops/changelog.py check-empty     # fail if any fragment is left
    python tools/ops/changelog.py check-pr BASE [TITLE] [AUTHOR]  # CI: a code PR
                                                # adds a fragment
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRAGMENTS = ROOT / "changelog.d"
CHANGELOG = ROOT / "CHANGELOG.md"
# Keep a Changelog order; the file suffix is the lower-case heading.
TYPES = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
# A PR touching only these needs no entry (docs, CI, the changelog itself).
# Spell out the paths that *ship*: the test is "would a user notice", and a
# directory of prose or workflow YAML never is.
CODE = ("src/", "tools/")
SKIP_MARK = "[skip changelog]"
#: Accounts whose pull requests are dependency bumps and nothing else.
BOTS = ("dependabot[bot]",)
#: The manifests only the toolchain reads. A bot moving these alone needs no
#: entry: its own PR body and the lockfile are the record, and a Keep a
#: Changelog bullet per patch bump is a line nobody reads. Everything a bot
#: could touch that *ships* — a runtime requirements file, a Dockerfile, deploy
#: config — still wants an entry, because a security fix in a dependency the
#: image carries is a change a user feels.
DEV_MANIFESTS = (
    "requirements-dev.txt",
    "package.json",
    "package-lock.json",
)
#: Manifests that hold both halves, where only one ships. A bump here is waved
#: through only if the shipping half is byte-identical before and after, which
#: `_runtime_deps` checks — otherwise "only the toolchain moved" is a guess.
SHIPPING_HALVES = ("package.json",)


def fragments() -> dict[str, list[Path]]:
    found: dict[str, list[Path]] = {t: [] for t in TYPES}
    bad = []
    for path in sorted(FRAGMENTS.glob("*.md")):
        if path.name == "README.md":
            continue
        kind = path.name.removesuffix(".md").rsplit(".", 1)[-1].capitalize()
        if kind not in found:
            bad.append(path.name)
            continue
        found[kind].append(path)
    if bad:
        sys.exit(f"unknown type in {', '.join(bad)} — use one of: {', '.join(t.lower() for t in TYPES)}")
    return found


def collect() -> int:
    found = fragments()
    if not any(found.values()):
        print("no fragments")
        return 0
    text = CHANGELOG.read_text(encoding="utf-8")
    start = text.index("## [Unreleased]\n") + len("## [Unreleased]\n")
    nxt = re.search(r"^## \[", text[start:], re.M)
    end = start + nxt.start() if nxt else len(text)
    body = text[start:end]
    for kind in TYPES:
        if not found[kind]:
            continue
        entries = "\n".join(p.read_text(encoding="utf-8").strip() + "\n" for p in found[kind])
        heading = re.search(rf"^### {kind}\n\n", body, re.M)
        if heading:
            # Newest first, as the section has always been written.
            body = body[: heading.end()] + entries + "\n" + body[heading.end() :]
        else:
            # Before the first later heading, so the Keep a Changelog order holds.
            later = [f"### {t}\n" for t in TYPES[TYPES.index(kind) + 1 :]]
            at = min((body.find(h) for h in later if h in body), default=-1)
            block = f"### {kind}\n\n{entries}\n"
            if at == -1:
                body = body.rstrip("\n") + "\n\n" + block
            else:
                body = body[:at] + block + body[at:]
    body = "\n" + body.strip("\n") + "\n\n"
    CHANGELOG.write_text(text[:start] + body + text[end:], encoding="utf-8")
    done = [p for ps in found.values() for p in ps]
    for path in done:
        path.unlink()
    print(f"folded {len(done)} fragment(s) into [Unreleased]")
    return 0


def check_empty() -> int:
    left = [p.name for ps in fragments().values() for p in ps]
    if left:
        print(f"changelog.d/ still has {len(left)} fragment(s) — run `make changelog` first")
        return 1
    return 0


def _runtime_deps(rev: str) -> dict[str, dict[str, str]]:
    """The shipping `dependencies` of every manifest in `SHIPPING_HALVES`, at one
    revision. A manifest the revision predates is absent rather than empty, so
    adding one is not mistaken for emptying it."""
    found: dict[str, dict[str, str]] = {}
    for manifest in SHIPPING_HALVES:
        done = subprocess.run(
            ["git", "show", f"{rev}:{manifest}"],
            capture_output=True,
            text=True,
            check=False,  # the revision may predate the file; that is not an error
            cwd=ROOT,
        )
        if done.returncode == 0:
            found[manifest] = dict(json.loads(done.stdout).get("dependencies", {}))
    return found


def check_pr(base: str, title: str = "", author: str = "") -> int:
    fragments()  # a misnamed fragment fails here, not at release time
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    ).stdout.split()
    if SKIP_MARK in title:
        print(f"{SKIP_MARK} in the title — not checking")
        return 0
    code = [f for f in changed if f.startswith(CODE)]
    if not code:
        print("no code changes — no entry needed")
        return 0
    # Only the code files are weighed: a bot touching something outside CODE as
    # well (its own config, say) is not a reason to demand an entry.
    if author in BOTS and all(f in DEV_MANIFESTS for f in code) and _runtime_deps(base) == _runtime_deps("HEAD"):
        print(f"{author}, and only the toolchain manifests moved — no entry needed")
        return 0
    if any(f.startswith("changelog.d/") and f != "changelog.d/README.md" for f in changed):
        print("ok — the PR adds a changelog fragment")
        return 0
    print(
        "This PR changes code but adds no changelog.d/<name>.<type>.md.\n"
        "See changelog.d/README.md, or put " + SKIP_MARK + " in the PR title if nobody would notice."
    )
    return 1


def main(argv: list[str]) -> int:
    if argv[:1] == ["collect"]:
        return collect()
    if argv[:1] == ["check-empty"]:
        return check_empty()
    if argv[:1] == ["check-pr"] and len(argv) in (2, 3, 4):
        return check_pr(*argv[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
