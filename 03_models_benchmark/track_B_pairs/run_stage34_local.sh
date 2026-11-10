#!/bin/sh
# Reproduction on a second machine, then Stage 3 (val sources) and Stage 4 ablations (plan 2026-11-09_1347).
# Waits for the streamed preprocessing, builds the injection cache, checks frozen hashes, then trains.
# Skips any step whose output already exists. Never reads test-split sets.
set -u
cd "$(dirname "$0")"
ROOT=../..
PRE=$ROOT/01_semi_synthetic_data/01_real_data
LOG=outputs_local
mkdir -p $LOG
until grep -q "^gallery:" $PRE/outputs/stream_preproc_run.log 2>/dev/null; do sleep 60; done  # preprocessing (and its gallery) finished
echo "preproc ready $(date +%H:%M)" >> $LOG/queue.log
if [ ! -f $ROOT/02_injection_labelling/01_injection/data/inject_cache_256.h5 ]; then
  (cd $PRE && python -u stream_preprocess.py --cache > outputs/stream_cache_run.log 2>&1) || { echo "cache FAILED" >> $LOG/queue.log; exit 1; }
fi
echo "cache ready $(date +%H:%M)" >> $LOG/queue.log
if [ ! -f $LOG/hashes.txt ]; then
  python -u - > $LOG/hashes.txt 2>&1 <<'EOF'
import sys, gc
sys.path.insert(0, "../../02_injection_labelling/01_injection")
from inject import load_pools, load_set, load_fold_set
P = load_pools()
for n in ("val", "val_bright"):
    load_set(n, P); print(n, "hash OK", flush=True); gc.collect()
for k in range(5):
    load_fold_set("dev", k, P); print(f"dev fold {k} hash OK", flush=True); gc.collect()
EOF
fi
echo "hashes: $(tr '\n' ' ' < $LOG/hashes.txt | tail -c 300)" >> $LOG/queue.log
run() {  # name, then train.py arguments
  name=$1; shift
  [ -f 01_training/outputs/$name/best.pt ] && [ -f $LOG/$name.done ] && { echo "skip $name" >> $LOG/queue.log; return; }
  echo "start $name $(date +%H:%M)" >> $LOG/queue.log
  (cd 01_training && python -u train.py "$@" --steps 20000 --eval-every 1000 --workers 4 > ../$LOG/run_$name.log 2>&1) \
    && touch $LOG/$name.done || echo "FAILED $name" >> $LOG/queue.log
  echo "end $name $(date +%H:%M) $(tail -1 $LOG/run_$name.log)" >> $LOG/queue.log
}
run m6_s0 --model 6 --seed 0
if [ ! -f 02_benchmark/outputs/stage3_val.txt ]; then
  echo "start stage3 $(date +%H:%M)" >> $LOG/queue.log
  (cd 02_benchmark && python -u transfer_check.py --model 6:../01_training/outputs/m6_s0/best.pt > ../$LOG/stage3.log 2>&1) || echo "stage3 FAILED" >> $LOG/queue.log
  echo "end stage3 $(date +%H:%M)" >> $LOG/queue.log
fi
run m6_s0_noalign --model 6 --seed 0 --no-align
run m6_s0_hardneg --model 6 --seed 0 --hardneg
run m6_s0_noimp --model 6 --seed 0 --no-impostors
echo "queue finished $(date +%H:%M)" >> $LOG/queue.log
