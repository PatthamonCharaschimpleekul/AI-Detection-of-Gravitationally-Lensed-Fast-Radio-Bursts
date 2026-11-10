#!/bin/sh
# Stage 4 ablations, seeds 1 and 2 (seed 0 ran in run_stage34_local.sh). Same command and worker count. Skips finished runs.
set -u
cd "$(dirname "$0")"
LOG=outputs_local
run() {  # name, then train.py arguments
  name=$1; shift
  [ -f 01_training/outputs/$name/best.pt ] && [ -f $LOG/$name.done ] && { echo "skip $name" >> $LOG/queue.log; return; }
  echo "start $name $(date +%H:%M)" >> $LOG/queue.log
  (cd 01_training && python -u train.py "$@" --steps 20000 --eval-every 1000 --workers 4 > ../$LOG/run_$name.log 2>&1) \
    && touch $LOG/$name.done || echo "FAILED $name" >> $LOG/queue.log
  echo "end $name $(date +%H:%M) $(tail -1 $LOG/run_$name.log)" >> $LOG/queue.log
}
for s in 1 2; do
  run m6_s$s --model 6 --seed $s
  run m6_s${s}_noalign --model 6 --seed $s --no-align
  run m6_s${s}_noimp --model 6 --seed $s --no-impostors
  run m6_s${s}_hardneg --model 6 --seed $s --hardneg
done
echo "stage4 seeds finished $(date +%H:%M)" >> $LOG/queue.log
