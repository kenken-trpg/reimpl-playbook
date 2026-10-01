#!/usr/bin/env python3
"""Fetch the reference implementation's files at a pinned commit.

Two reasons this is a script and not a git submodule or a vendored copy:

* **Licence.** The reference's data is usually under a licence that makes
  copying it into your repository a decision, and often a wrong one. Fetching
  at setup time keeps your tree your own code. (`vendor/` is gitignored.)
* **Reproducibility.** The subject parses the reference's schema, and that
  schema changes on the reference's default branch without notice. A pin
  turns "the tests broke overnight" into "somebody bumped the pin".

The pin is the whole point, so moving it is a deliberate act with a procedure:
bump `--ref` (or `DEFAULT_REF` in your copy), re-fetch, run the full suite
*and* the oracle harness, and commit the new SHA together with whatever
parser changes it needed. An upstream fix you contributed does not reach your
code until you do this.

Re-running is cheap: it skips the download when `vendor/` already holds every
file for the requested ref, so `make data` can sit in front of everything.

    python tools/pin/fetch_upstream.py                 # the pinned ref
    python tools/pin/fetch_upstream.py --ref <sha>     # move it
    python tools/pin/fetch_upstream.py --force         # re-fetch anyway
    python tools/pin/fetch_upstream.py --corpus        # also the test corpus

CI should cache `vendor/` keyed on **the hash of this script**, not on the
ref: that way adding a file to `FILES` invalidates the cache too, which a
key on the ref alone would miss.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# --- Fill these in for your project ----------------------------------------

#: owner/repo of the reference implementation.
UPSTREAM = "example/reference-implementation"

#: The commit everything is read at. A tag or a branch would defeat the point.
DEFAULT_REF = "0000000000000000000000000000000000000000"

#: The files the subject actually parses, spelled out. A glob would quietly
#: start pulling in whatever upstream adds next.
FILES: list[str] = [
    "data/example.xml",
]

#: A directory of the reference's own test artefacts, or None. These are the
#: corpus the oracle harness runs over, and taking them from the *same* ref as
#: the data matters: what the comparison is checked against and what it
#: computes from then come from one release.
CORPUS_DIR: str | None = None

# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "vendor" / "upstream"
CORPUS = ROOT / "vendor" / "upstream-corpus"
REF_FILE = VENDOR / ".upstream-ref"
RAW = "https://raw.githubusercontent.com"


def _get(url: str, headers: dict[str, str] | None = None, tries: int = 3) -> bytes:
    """`url`, retried. A CDN hiccup is not a reason to fail a fresh checkout."""
    last: Exception | None = None
    for attempt in range(tries):
        if attempt:
            time.sleep(2**attempt)
        try:
            request = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(request, timeout=60) as response:
                return bytes(response.read())
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
    raise SystemExit(f"could not fetch {url}: {last}")


def _api(url: str) -> Any:
    """The GitHub API, signed in if this environment has a token.

    Raw file downloads are not rate limited, but *listing* a directory is an
    API call — and unauthenticated that is 60 an hour per IP, which on a
    shared CI runner can be spent before the job starts. `GITHUB_TOKEN` in
    Actions raises it to 5,000.
    """
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "reimpl-playbook"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return json.loads(_get(url, headers))


def ref() -> str:
    """The ref `vendor/` currently holds, or the pin if it holds nothing."""
    return REF_FILE.read_text(encoding="utf-8").strip() if REF_FILE.exists() else DEFAULT_REF


def _download(path: str, into: Path, at: str) -> None:
    target = into / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_get(f"{RAW}/{UPSTREAM}/{at}/{path}"))


def fetch(at: str, force: bool = False) -> bool:
    """Download `FILES` at `at`. Returns False if nothing had to be done."""
    have = ref() == at and all((VENDOR / path).exists() for path in FILES)
    if have and not force:
        return False
    VENDOR.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda path: _download(path, VENDOR, at), FILES))
    REF_FILE.write_text(at + "\n", encoding="utf-8")
    return True


def fetch_corpus(at: str, force: bool = False) -> int:
    """Download every file under `CORPUS_DIR` at `at`. Returns how many."""
    if CORPUS_DIR is None:
        return 0
    if CORPUS.exists() and any(CORPUS.iterdir()) and not force:
        return len(list(CORPUS.iterdir()))
    CORPUS.mkdir(parents=True, exist_ok=True)
    listing = _api(f"https://api.github.com/repos/{UPSTREAM}/contents/{CORPUS_DIR}?ref={at}")
    names = [entry["path"] for entry in listing if entry["type"] == "file"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda path: _download(path, CORPUS, at), names))
    return len(names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--corpus", action="store_true", help="also the test corpus")
    args = parser.parse_args(argv)
    if fetch(args.ref, args.force):
        print(f"fetched {len(FILES)} files at {args.ref[:12]} into {VENDOR}")
    else:
        print(f"up to date at {args.ref[:12]}")
    if args.corpus:
        print(f"corpus: {fetch_corpus(args.ref, args.force)} files in {CORPUS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
