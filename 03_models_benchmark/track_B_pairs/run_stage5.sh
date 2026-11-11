#!/bin/sh
# Stage 5 (plan 2026-11-06_1223 + addendum 2026-11-08_0845 F8): the one test opening, local machine only.
# Primary first: model 6 and the per-fold GBM on scheme 'all' (5 folds over all 80 sources), then the F7 OOF metric.
# Secondary after: models 4, 5, 7 per fold (ablations). Settings exactly F4-F6; 4 data workers (RAM). Skips finished runs.
set -u
cd "$(dirname "$0")"
LOG=outputs_local/stage5_queue.log
say() { echo "$* $(date +%H:%M)" >> $LOG; }
learned() {  # model fold
  [ -f 01_training/outputs/folds_all/m$1_f$2/fold_scores.npz ] && { say "skip m$1 f$2"; return; }
  say "start m$1 f$2"
  (cd 01_training && python -u train.py --model $1 --fold $2 --scheme all --steps 20000 --eval-every 1000 --workers 4 \
     > ../outputs_local/stage5_m$1_f$2.log 2>&1) || say "FAILED m$1 f$2"
  say "end m$1 f$2: $(tail -1 outputs_local/stage5_m$1_f$2.log)"
}
gbm() {
  [ -f 02_benchmark/outputs/folds_all/gbm_f$1.npz ] && { say "skip gbm f$1"; return; }
  say "start gbm f$1"
  (cd 02_benchmark && python -u stage5_fold_baselines.py $1 > ../outputs_local/stage5_gbm_f$1.log 2>&1) || say "FAILED gbm f$1"
  say "end gbm f$1: $(tail -1 outputs_local/stage5_gbm_f$1.log)"
}
say "stage5 begin (benchmark-v1 $(git rev-parse --short benchmark-v1^{commit}))"
for k in 0 1 2 3 4; do learned 6 $k; gbm $k; done
(cd 02_benchmark && python -u folds_oof.py --scheme all --models 6 > ../outputs_local/stage5_oof_primary.log 2>&1) || say "FAILED oof primary"
say "primary done"
for m in 5 4 7; do for k in 0 1 2 3 4; do learned $m $k; done; done
(cd 02_benchmark && python -u folds_oof.py --scheme all --models 6,4,5,7 > ../outputs_local/stage5_oof_all.log 2>&1) || say "FAILED oof all"
say "stage5 finished"
