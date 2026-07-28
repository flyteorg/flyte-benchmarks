# Reference results

Numbers we measured on identical 8 GiB orchestrator pods (core-sleep leaves, no
task pods). Use these to sanity-check your own runs — exact values depend on
cluster size, DB, and network, but the *shape* (v2 >> v1; Union clears the
swarm OSS OOMs on) should reproduce.

## Swarm — K runs x 2,000 leaves, 1 s sleep (the scale / OOM test)

| K | total actions | Flyte v2 (OSS) wall | OSS peak mem | Union wall |
|---|---|---|---|---|
| 2   | 4,000   | 102 s   | ~0.6 GiB | 59 s |
| 5   | 10,000  | 229 s   | ~0.8 GiB | 123 s |
| 10  | 20,000  | 440 s   | ~2.0 GiB | 185 s |
| 25  | 50,000  | 1,333 s | 2.6 GiB  | 418 s |
| 50  | 100,000 | 3,617 s (48/50) | 5.3 GiB | 772 s |
| 100 | 200,000 | **OOM-killed** (peak 8.1 GiB) | — | **1,533 s (100/100)** |

OSS executor memory tracks *cumulative* actions at ~54 MiB / 1,000 (~55 KB/object)
and OOMs an 8 GiB pod near ~150k cumulative actions. Union keeps action state in
ScyllaDB and completes 200k.

### All three at the low end, same day (2026-07-27)

v1 was never run at the scales above — it took 326 s for 10k actions here, so the
200k point would run for hours. At a scale all three handle:

| total actions | Flyte v1 | Flyte v2 (OSS) | Union |
|---|---|---|---|
| 4,000  | 300.8 s | 69.2 s  | 54.1 s |
| 10,000 | 325.6 s | 168.8 s | 71.3 s |

## Wide fan-out — one run, N leaves, 0 s sleep

| leaves | Flyte v1 | Flyte v2 |
|---|---|---|
| 1,000 | 124 s | 29 s |
| 6,000 | 717 s | 115 s |

Under *held* leaves (120 s), v1 OOMs its single CRD at ~6,000 held; v2 stays flat.

### All three, same day (2026-07-27 re-run)

Execution seconds (submit excluded), same driver, all three clusters on one day.
A fan-out has thousands of actions live at once, so the scaled-out orchestrator
has something to parallelize — and does:

| leaves | Flyte v1 | Flyte v2 (OSS) | Union | Union vs v1 |
|---|---|---|---|---|
| 1,000 | 126.3 s | 68.4 s | 19.0 s | 6.6× |
| 3,000 | 371.8 s | 144.2 s | 39.0 s | 9.5× |
| 6,000 | 699.1 s | 355.6 s | 68.6 s | 10.2× |

v1 reproduces its older numbers closely (699 s vs 717 s at 6,000), but this v2
build is much slower than the one above (356 s vs 115 s) — so compare within a
table, not across them.

## Long chain — N nodes in series, 0 s sleep

| length | Flyte v1 | Flyte v2 |
|---|---|---|
| 100 | 74 s | 16 s |
| 500 | 365 s | 56 s |

Peak orchestrator memory over the sweep: v1 1,272 → 1,589 MiB (grows with the
run); v2 flat at 298 → 327 MiB.

### All three, same day (2026-07-24 / 07-27 re-run)

Union and a single-pod OSS v2 are **indistinguishable** here — a chain executes
one action at a time, so scaling the orchestrator out has nothing to work with. Wall-clock
is `length × per-transition latency`, the same runs-service → executor →
runs-service round trip in both. Union's advantage shows up in the concurrent
shapes (swarm, held concurrency), not this one.

Execution seconds (submit excluded), same driver and day on both clusters:

| length | Flyte v1 | Flyte v2 (OSS) | Union | v2/Union per-node |
|---|---|---|---|---|
| 100 | 65.7 s | 18.9 s | 19.0 s | ~0.19 s |
| 300 | 202.8 s | 53.4 s | 53.5 s | ~0.18 s |
| 500 | 366.1 s | 83.5 / 83.6 s | 83.7 s | ~0.17 s |

(v1 measured 2026-07-27, v2/Union 2026-07-24; v2 re-measured 18.9 s at length 100
on the 27th, so the two days agree.)

OSS executor over the whole sweep (1,900 actions, 8 GiB pod): peak **331 MiB**,
0 restarts — matching the 327 MiB above. Union's orchestrator is hosted and
multi-tenant, so a pod-RSS number there isn't comparable and was not taken.

Note both v2 and Union ran ~0.167 s/node here versus ~0.11 s/node in the v1-vs-v2 rows
above (56 s at length=500), on newer builds. Two independent clusters landing
within 0.2 s of each other points at the per-transition path rather than cluster
noise; treat the older long-chain wall-clocks as build-specific.

## Concurrency — K runs x 1,000 tasks held live 120 s

| held tasks | Flyte v1 | Flyte v2 | peak mem (v2/OSS) |
|---|---|---|---|
| 1,000  | 242 s   | 146 s | ~0.7 GiB |
| 10,000 | —       | —     | ~1.6 GiB |
| 20,000 | —       | —     | ~2.0 GiB |
| 40,000 | 1,016 s | 756 s | ~3.5 GiB |

Headline: v2 beats v1 on every workload here — ~2× on a fan-out, ~3.5–4.4× on a
long chain, ~1.2–1.7× on held concurrency in the same-day runs (an earlier v2
build was faster still, up to 6.5×) — and removes v1's per-run OOM cliff. Moving
action state off the executor's cache (Union/ScyllaDB) removes the per-deployment
cliff at six-figure action counts.
