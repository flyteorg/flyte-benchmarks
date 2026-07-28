#!/usr/bin/env bash
# Sample peak working-set memory + OOM/restart of the orchestration pod during a
# benchmark run. Run this in a second terminal while a workload is executing.
#
# Usage:
#   NS=flyte SEL='app.kubernetes.io/name=flyte-binary' CONT=flyte ./sample_mem.sh [seconds]
#
#   NS   = namespace                (default: flyte)
#   SEL  = pod label selector       (v1/OSS flyte-binary: app.kubernetes.io/name=flyte-binary)
#   CONT = container name           (default: flyte)
#
# Requires: kubectl access to the cluster + metrics-server (for `kubectl top`).
# Prints:  PEAK_MEM_MIB=<n> RESTARTS_DELTA=<n>   (RESTARTS_DELTA>0 => OOM/restart during the window)
set -euo pipefail
NS="${NS:-flyte}"; SEL="${SEL:-app.kubernetes.io/name=flyte-binary}"; CONT="${CONT:-flyte}"
DUR="${1:-1800}"; peak=0; start=$SECONDS
pod=$(kubectl -n "$NS" get pod -l "$SEL" -o jsonpath='{.items[0].metadata.name}')
[ -z "$pod" ] && { echo "no pod matched -l $SEL in ns $NS" >&2; exit 1; }
jp="{.status.containerStatuses[?(@.name=='$CONT')].restartCount}"
r0=$(kubectl -n "$NS" get pod "$pod" -o jsonpath="$jp"); r0=${r0:-0}
echo "sampling $NS/$pod ($CONT) for ${DUR}s; start restarts=$r0"
r=$r0
while [ $((SECONDS - start)) -lt "$DUR" ]; do
  m=$(kubectl -n "$NS" top pod "$pod" --no-headers 2>/dev/null | awk '{print $3}' | sed 's/Mi//')
  if [ -n "${m:-}" ] && [ "$m" -gt "$peak" ] 2>/dev/null; then peak=$m; fi
  r=$(kubectl -n "$NS" get pod "$pod" -o jsonpath="$jp" 2>/dev/null || echo "$r0"); r=${r:-$r0}
  if [ "$r" -gt "$r0" ] 2>/dev/null; then
    echo "!! OOM/restart detected (restarts $r0 -> $r) at peak=${peak}Mi (exit 137 = OOMKilled)"
    break
  fi
  sleep 5
done
echo "PEAK_MEM_MIB=$peak RESTARTS_DELTA=$(( r - r0 ))"
