# Reference results

Numbers we measured on identical 8 GiB orchestration pods (core-sleep leaves, no
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

## Wide fan-out — one run, N leaves, 0 s sleep

| leaves | Flyte v1 | Flyte v2 |
|---|---|---|
| 1,000 | 124 s | 29 s |
| 6,000 | 717 s | 115 s |

Under *held* leaves (120 s), v1 OOMs its single CRD at ~6,000 held; v2 stays flat.

## Long chain — N nodes in series, 0 s sleep

| length | Flyte v1 | Flyte v2 |
|---|---|---|
| 100 | 74 s | 16 s |
| 500 | 365 s | 56 s |

## Concurrency — K runs x 1,000 tasks held live 120 s

| held tasks | Flyte v1 | Flyte v2 | peak mem (v2/OSS) |
|---|---|---|---|
| 1,000  | 242 s   | 146 s | ~0.7 GiB |
| 10,000 | —       | —     | ~1.6 GiB |
| 20,000 | —       | —     | ~2.0 GiB |
| 40,000 | 1,016 s | 756 s | ~3.5 GiB |

Headline: v2 runs the common patterns ~4.3–6.5x faster than v1 and removes v1's
per-run OOM cliff; moving state off the executor's cache (Union/ScyllaDB) removes
the per-deployment cliff at six-figure action counts.
