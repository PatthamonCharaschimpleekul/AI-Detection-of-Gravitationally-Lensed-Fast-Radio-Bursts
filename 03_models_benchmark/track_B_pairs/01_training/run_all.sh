#!/bin/sh
# Stage 2 full runs: same step budget for all models, 3 seeds each (update 2026-11-06_1431).
cd "$(dirname "$0")"
for m in 6 5 4 7; do
  for s in 0 1 2; do
    ../../../venv/Scripts/python -I train.py --model $m --seed $s --steps 20000 --eval-every 1000 --workers 12 > outputs/run_m${m}_s${s}.log 2>&1
    echo "m$m s$s exit $? $(date +%H:%M) $(tail -1 outputs/run_m${m}_s${s}.log)" >> outputs/run_all.log
  done
done
