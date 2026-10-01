PY ?= python3

.PHONY: setup test example lint data corpus check

setup:
	$(PY) -m pip install -q pytest

test:
	$(PY) -m pytest -q tests

example:
	$(PY) -m tools.oracle.cli --adapter example.adapter --corpus example/corpus

# What CI gates on: the harness must stay clean on the checks that start clean.
check:
	$(PY) -m tools.oracle.cli --adapter example.adapter --corpus example/corpus \
		--only roundtrip --only fidelity --gate

data:
	$(PY) tools/pin/fetch_upstream.py

corpus:
	$(PY) tools/pin/fetch_upstream.py --corpus

doctor:
	./tools/ops/doctor.sh
