#!/bin/sh
# Grouped-fold rehearsal (plan 2026-11-08_0845 F9): model 6 on 5 dev folds, then the GBM per fold, then the OOF report.
# timeout: a CUDA error once left a run hanging for an hour (update 2026-11-08_0640).
cd "$(dirname "$0")"
mkdir -p outputs/folds_dev
PY=../../../venv/Scripts/python
for k in 0 1 2 3 4; do
  timeout 2h $PY -I train.py --model 6 --fold $k --scheme dev --steps 20000 --eval-every 1000 --workers 12 > outputs/folds_dev/run_m6_f$k.log 2>&1
  echo "m6 f$k exit $? $(date +%H:%M) $(tail -1 outputs/folds_dev/run_m6_f$k.log)" >> outputs/folds_dev/run_folds.log
done
for k in 0 1 2 3 4; do
  (cd ../02_benchmark && $PY -I baselines.py --fold $k --scheme dev) > outputs/folds_dev/run_gbm_f$k.log 2>&1
  echo "gbm f$k exit $? $(date +%H:%M) $(tail -1 outputs/folds_dev/run_gbm_f$k.log)" >> outputs/folds_dev/run_folds.log
done
(cd ../02_benchmark && $PY -I folds_oof.py --scheme dev) >> outputs/folds_dev/run_folds.log 2>&1
