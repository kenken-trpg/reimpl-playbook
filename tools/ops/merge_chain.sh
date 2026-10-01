#!/usr/bin/env bash
# Rebase, check and merge a queue of PRs, one after another.
#
#   tools/ops/merge_chain.sh 248:feat/one 249:feat/two
#
# Configure it in `merge_chain.conf.sh` beside this file: which paths are a
# "half" of the tree, how to check each half, and which conflicts may be
# resolved by keeping both sides.
#
# Disarm auto-merge on the whole queue first (`gh pr merge <n> --disable-auto`).
# main is protected with `strict`, so a branch has to be up to date to merge: a
# PR left armed can merge on its own, move main, and strand the PR this run just
# rebased at BEHIND — which ends the run at the STOP below, five minutes after
# its checks all went green. Merges have to come from here and nowhere else.
#
# Each PR is rebased onto the current origin/main (so the one before it is
# already in), checked the way CI checks it, pushed, and — once *every* check
# on GitHub has reported green, not only the required ones — handed to
# auto-merge. The run waits for that merge anyway: the next PR rebases onto a
# main that contains this one.
#
# A conflict in a `KEEP_BOTH` path keeps both sides — two changelog entries or
# two test cases are what the two branches meant. Any other conflict stops the
# run for a human. Be stingy with `KEEP_BOTH`: a translation dictionary looks
# appendable and is not, because a conflicting wording is a choice and a
# duplicated key only surfaces at runtime. The run ends on the default branch,
# up to date.
set -u
cd "$(dirname "$0")/../.."
here=$(pwd)
keepboth=tools/ops/keep_both_sides.py
# shellcheck source=merge_chain.conf.sh
. "$here/tools/ops/merge_chain.conf.sh"

for pair in "$@"; do
  n=${pair%%:*}; br=${pair#*:}
  echo "=== #$n $br"
  if [ "$(gh pr view "$n" --json state -q .state)" = MERGED ]; then echo "already merged"; continue; fi
  git fetch -q origin
  git switch -q "$br" || exit 1
  # Where this branch sat before the rebase, so that what main gained since can
  # be told apart from what the branch itself changes.
  was=$(git merge-base HEAD origin/main)
  if ! git rebase origin/main >/dev/null 2>&1; then
    while true; do
      files=$(git diff --name-only --diff-filter=U)
      [ -z "$files" ] && break
      for f in $files; do
        case "$f" in
          $KEEP_BOTH) python3 "$keepboth" "$f" || exit 1 ;;
          *) echo "STOP: conflict in $f"; exit 1 ;;
        esac
        if grep -q '^<<<<<<<\|^>>>>>>>' "$f"; then echo "STOP: markers left in $f"; exit 1; fi
        git add "$f"
      done
      GIT_EDITOR=true git rebase --continue >/dev/null 2>&1 || true
      git status | grep -q "rebase in progress" || break
    done
  fi
  # Which half to check. The point of checking at all is that the default
  # branch may have moved under this one, so it is not enough to ask what the
  # branch changes: both sides count. If neither touched a half, the green this
  # PR already has for it still stands and running it again buys nothing.
  #
  # Anything outside the declared halves runs everything, because what it
  # reaches is not written down anywhere this could read — the Makefile and
  # tools/ are what the checks are invoked *through*. Prose is the exception,
  # and it has to be: every PR carries a changelog fragment, so counting those
  # as `elsewhere` would open every gate every time and this would decide
  # nothing.
  touched=$( (git diff --name-only origin/main...HEAD; git diff --name-only "$was" origin/main) | sort -u)
  elsewhere=$(printf '%s\n' "$touched" | grep -vE "$PROSE")
  for half in $HALVES; do
    eval "prefix=\$HALF_${half}_PATH"
    if [ -n "$elsewhere" ] || printf '%s\n' "$touched" | grep -q "^$prefix"; then
      "check_$half" || { echo "STOP: $half checks"; exit 1; }
    else
      echo "$half untouched on both sides — checked already"
    fi
  done
  # Formatting the tree is part of the checks above, so a rebase that left a
  # file unformatted gets its own commit rather than a dirty tree at push.
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    git commit -qam "style: format after rebase"
  fi
  git push -q --force-with-lease origin "$br" || exit 1
  # Wait for GitHub to agree that the head is what was just pushed, rather than
  # guessing how long that takes. `gh pr checks` reports the checks of the PR's
  # head commit, so once the two match, what it lists is this push's — which is
  # what the blind `sleep 20` here was reaching for, less certainly and more
  # slowly (it usually settles in a few seconds).
  head=$(git rev-parse HEAD)
  seen=
  for _ in $(seq 1 20); do
    seen=$(gh pr view "$n" --json headRefOid -q .headRefOid 2>/dev/null)
    [ "$seen" = "$head" ] && break
    sleep 3
  done
  [ "$seen" = "$head" ] || { echo "STOP: GitHub still does not see the push after 1 min"; exit 1; }
  # Wait for every check to report, and require all of them green, BEFORE
  # handing the PR to auto-merge. The other order merged a PR with one of its
  # non-required jobs red: a STOP here is only this script exiting, while
  # `--auto` is an instruction GitHub keeps and acts on, and GitHub waits for
  # the checks branch protection calls *required* — not for the ones this loop
  # reads. Arming it only once everything has reported means the two cannot
  # disagree about what green is.
  # Ten seconds rather than twenty: the wait is idle either way, and the run
  # spends it once per PR. At worst this asks 120 times per PR here and 60
  # below — nowhere near the 5,000 requests an hour the API allows.
  pending=
  for _ in $(seq 1 120); do
    # `|| true`, not `|| checks=`: gh exits 1 exactly when a check has failed,
    # and throwing the output away then would hide the one thing this looks for.
    checks=$(gh pr checks "$n" 2>/dev/null || true)
    bad=$(printf '%s\n' "$checks" | grep -v -E "\bpass\b|\bpending\b|skipping")
    if [ -n "$bad" ]; then echo "STOP: checks"; echo "$bad"; exit 1; fi
    pending=$(printf '%s\n' "$checks" | grep -c "\bpending\b")
    [ "$pending" = 0 ] && [ -n "$checks" ] && break
    sleep 10
  done
  [ "$pending" = 0 ] || { echo "STOP: checks still pending after 20 min"; exit 1; }
  gh pr merge "$n" --squash --auto >/dev/null 2>&1 ||
    { echo "STOP: could not enable auto-merge"; exit 1; }
  # The queue still has to wait: the next PR is rebased onto a main that
  # contains this one. Everything has reported by now, so this is short — and
  # if it does not merge, auto-merge is disarmed on the way out rather than
  # left to merge the branch later, unattended, after a STOP.
  state=
  for _ in $(seq 1 60); do
    state=$(gh pr view "$n" --json state -q .state)
    [ "$state" = MERGED ] && break
    sleep 5
  done
  if [ "$state" != MERGED ]; then
    gh pr merge "$n" --disable-auto >/dev/null 2>&1 || true
    echo "STOP: not merged 5 min after every check reported (auto-merge disarmed)"
    exit 1
  fi
  # The remote branch goes with the repository's delete-on-merge setting; the
  # local one is ours to clean up, and cannot be deleted while checked out.
  git switch -q main && git branch -qD "$br"
  echo "merged #$n"
done
cd "$here" && git switch -q main && git pull -q --ff-only && echo DONE
