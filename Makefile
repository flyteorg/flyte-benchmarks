# Flyte benchmark suites. Pick the plane with V=v1 or V=v2 (default v2); every
# shape takes the same knobs on both, so the same command line compares planes.
#
#   make fanout V=v2 N=6000
#   make fanout V=v1 N=6000
#
# Run `make help` for the full list.

SKILL   := flyte-benchmark/skills/flyte-benchmark
S       := $(SKILL)/scripts
PY      ?= python
V       ?= v2
RESULTS ?= results.jsonl

# Workload knobs. Keep comments off the assignment lines — make would keep the
# trailing spaces as part of the value.
# N     fan-out leaves
# L     chain length
# M     held tasks (concurrency), or held leaves per run (v1 swarm)
# K     concurrent runs (swarm)
# HOLD  seconds to hold tasks live
# SLEEP leaf sleep seconds
N       ?= 1000
L       ?= 100
M       ?= 1000
K       ?= 10
HOLD    ?= 120
SLEEP   ?= 0
DEPTH   ?= 20
WIDTH   ?= 5
TIMEOUT ?= 1800

# Memory sampler: v2 / OSS single-binary pod by default.
# For v1: make mem SEL=app.kubernetes.io/name=flytepropeller CONT=flytepropeller
NS   ?= flyte
SEL  ?= app.kubernetes.io/name=flyte-binary
CONT ?= flyte

ifeq ($(V),v1)
  RUNNER      := $(S)/v1/_runner.py
  SWARM       := $(S)/v1/swarm.py
  REQS        := $(S)/v1/requirements.txt
  FANOUT_ARGS  = --n_children $(N) --sleep_duration $(SLEEP)s
  CHAIN_ARGS   = --length $(L) --sleep_duration $(SLEEP)s
  CONC_ARGS    = --m $(M) --hold_seconds $(HOLD)
  NESTED_ARGS  = --depth $(DEPTH) --width $(WIDTH) --sleep_duration $(SLEEP)s
  SWARM_ARGS   = --k $(K) --m $(M) --hold_seconds $(HOLD)
else
  RUNNER      := $(S)/v2/_runner.py
  SWARM       := $(S)/v2/swarm.py
  REQS        := $(S)/v2/requirements.txt
  FANOUT_ARGS  = n_children=$(N) sleep_seconds=$(SLEEP)
  CHAIN_ARGS   = length=$(L) sleep_seconds=$(SLEEP)
  CONC_ARGS    = m=$(M) hold_seconds=$(HOLD)
  NESTED_ARGS  = depth=$(DEPTH) width=$(WIDTH) sleep_seconds=$(SLEEP)
  SWARM_ARGS   = --k $(K) --n_children $(N) --sleep_seconds 1 --timeout $(TIMEOUT) --max-retries 0
endif

.PHONY: help install fanout long_chain concurrency nested swarm \
        sweep sweep-fanout sweep-chain sweep-conc sweep-swarm mem report charts clean

help:
	@echo "Flyte benchmarks — set V=v1 or V=v2 (current: $(V))"
	@echo
	@echo "  make install                 install this plane's SDK into the active venv"
	@echo "  make fanout      N=$(N)      one run, N parallel leaves"
	@echo "  make long_chain  L=$(L)       L nodes in series"
	@echo "  make concurrency M=$(M) HOLD=$(HOLD)   hold M leaves live"
	@echo "  make nested      DEPTH=$(DEPTH) WIDTH=$(WIDTH)      nested subworkflows"
	@echo "  make swarm       K=$(K)         K concurrent runs (the scale/OOM test)"
	@echo
	@echo "  make sweep                   the recommended sweep for this plane"
	@echo "  make mem [SEL=... CONT=...]  sample peak memory + OOM (second terminal)"
	@echo "  make report                  summary table + charts from $(RESULTS)"
	@echo "  make charts                  regenerate the README charts"
	@echo
	@echo "Results append to $(RESULTS). Select the cluster with FLYTE_BENCH_CONFIG."
	@echo "v1 and v2 need separate venvs — flytekit and the v2 SDK cannot coexist."

install:
	$(PY) -m pip install -r $(REQS)

fanout:
	$(PY) $(RUNNER) fanout $(FANOUT_ARGS) | tee -a $(RESULTS)

long_chain:
	$(PY) $(RUNNER) long_chain $(CHAIN_ARGS) | tee -a $(RESULTS)

concurrency:
	$(PY) $(RUNNER) concurrency $(CONC_ARGS) | tee -a $(RESULTS)

nested:
	$(PY) $(RUNNER) nested $(NESTED_ARGS) | tee -a $(RESULTS)

swarm:
	$(PY) $(SWARM) $(SWARM_ARGS) | tee -a $(RESULTS)

# --- sweeps (the ranges in reference_results.md) --------------------------
sweep: sweep-fanout sweep-chain sweep-conc

sweep-fanout:
	for n in 1000 2000 3000 4000 5000 6000; do $(MAKE) fanout N=$$n; done

sweep-chain:
	for l in 100 300 500; do $(MAKE) long_chain L=$$l; done

sweep-conc:
	for m in 1000 5000 10000 20000 40000; do $(MAKE) concurrency M=$$m; done

# ramps to 200k actions on v2; on v1 it ramps held leaves instead
sweep-swarm:
	for k in 2 5 10 25 50 100; do $(MAKE) swarm K=$$k N=2000; done

# --- support --------------------------------------------------------------
mem:
	NS=$(NS) SEL='$(SEL)' CONT=$(CONT) $(S)/sample_mem.sh $(TIMEOUT)

report:
	$(PY) $(S)/plot_results.py $(RESULTS) --out charts

charts:
	$(PY) charts/make_charts.py

clean:
	rm -f $(RESULTS) charts_*.png
	find $(S) -name __pycache__ -type d -exec rm -rf {} +
