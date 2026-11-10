#!/bin/sh
# Runs the remaining POC experiments one at a time, skipping finished runs.
# Order: does capacity close the power gap (G1), then seed noise (G3), then finite data.
run() { # method seed finite steps width
  name="$1_w$5_s$4"; [ "$3" != 0 ] && name="${name}_finite$3"; name="${name}_seed$2"
  [ -f "outputs/runs/$name/meta.json" ] && { echo "skip $name"; return; }
  echo "start $name $(date +%H:%M)"
  python train.py --method "$1" --seed "$2" --finite "$3" --steps "$4" --width "$5" > "outputs/logs/$name.log" 2>&1 || echo "FAILED $name"
}
run plain 0 0 30000 96
run plain 0 0 60000 48
for seed in 1 2; do for m in plain naive iw cond; do run $m $seed 0 30000 48; done; done
for m in plain naive iw cond; do run $m 0 4539 30000 48; done
echo "queue finished $(date +%H:%M)"
