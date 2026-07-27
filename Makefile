# Flyte benchmarks. Pick the plane with V=v1 or V=v2 (default v2); both planes
# take the same flags, so comparing them is the same command twice:
#
#   make fanout V=v2 N=6000
#   make fanout V=v1 N=6000
#
# Everything runs through `uv run`, which resolves each script's dependencies
# from its own PEP 723 header — no venv to create or activate.
# Run `make help` for the full list.

S       := flyte-benchmark/skills/flyte-benchmark/scripts
UV      ?= uv run
V       ?= v2
RESULTS ?= results.jsonl

# Workload knobs. Keep comments off the assignment lines — make would keep the
# trailing spaces as part of the value.
# N     fan-out leaves (per run)
# L     chain length
# M     held tasks
# K     concurrent runs (swarm)
# HOLD  seconds to hold tasks live
# SLEEP leaf sleep seconds
N       ?= 1000
L       ?= 100
M       ?= 1000
K       ?= 10
HOLD    ?= 120
SLEEP   ?= 0
TIMEOUT ?= 1800

# Memory sampler: v2 / OSS single-binary pod by default.
# For v1: make mem SEL=app.kubernetes.io/name=flytepropeller CONT=flytepropeller
NS   ?= flyte
SEL  ?= app.kubernetes.io/name=flyte-binary
CONT ?= flyte

RUN := $(UV) $(S)/$(V)

.PHONY: help fanout long_chain concurrency swarm \
        sweep sweep-fanout sweep-chain sweep-conc sweep-swarm mem report charts clean

help:
	@echo "Flyte benchmarks — set V=v1 or V=v2 (current: $(V))"
	@echo
	@echo "  make fanout      N=$(N)              one run, N parallel leaves"
	@echo "  make long_chain  L=$(L)               L nodes in series"
	@echo "  make concurrency M=$(M) HOLD=$(HOLD)      hold M leaves live"
	@echo "  make swarm       K=$(K) N=$(N)         K concurrent runs (the scale/OOM test)"
	@echo
	@echo "  make sweep                          fanout + chain + concurrency ranges"
	@echo "  make sweep-swarm                    ramp K 2 -> 100 (up to 200k actions)"
	@echo "  make mem [SEL=... CONT=...]         peak memory + OOM (second terminal)"
	@echo "  make report                         summary table + charts from $(RESULTS)"
	@echo "  make charts                         regenerate the README charts"
	@echo
	@echo "Results append to $(RESULTS). Pick the cluster with FLYTE_BENCH_CONFIG."

fanout:
	$(RUN)/fanout.py --n $(N) --sleep $(SLEEP) --timeout $(TIMEOUT) | tee -a $(RESULTS)

long_chain:
	$(RUN)/long_chain.py --length $(L) --sleep $(SLEEP) --timeout $(TIMEOUT) | tee -a $(RESULTS)

concurrency:
	$(RUN)/concurrency.py --m $(M) --hold $(HOLD) --timeout $(TIMEOUT) | tee -a $(RESULTS)

swarm:
	$(RUN)/swarm.py --k $(K) --n $(N) --sleep 1 --timeout $(TIMEOUT) | tee -a $(RESULTS)

# --- sweeps (the ranges in reference_results.md) --------------------------
sweep: sweep-fanout sweep-chain sweep-conc

sweep-fanout:
	for n in 1000 2000 3000 4000 5000 6000; do $(MAKE) fanout N=$$n; done

sweep-chain:
	for l in 100 300 500; do $(MAKE) long_chain L=$$l; done

sweep-conc:
	for m in 1000 5000 10000 20000 40000; do $(MAKE) concurrency M=$$m; done

sweep-swarm:
	for k in 2 5 10 25 50 100; do $(MAKE) swarm K=$$k N=2000; done

# --- support --------------------------------------------------------------
mem:
	NS=$(NS) SEL='$(SEL)' CONT=$(CONT) $(S)/sample_mem.sh $(TIMEOUT)

report:
	$(UV) $(S)/plot_results.py $(RESULTS) --out charts

charts:
	$(UV) charts/make_charts.py

clean:
	rm -f $(RESULTS) charts_*.png
	find $(S) -name __pycache__ -type d -exec rm -rf {} +
