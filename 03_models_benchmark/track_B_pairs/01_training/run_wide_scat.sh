#!/bin/sh
# Wide-scattering training (plan 2026-11-11_1400): model 6, tau600 up to 10 ms in training, seeds 0-2, then evaluation + sweep.
cd "$(dirname "$0")"
PY=../../../venv/Scripts/python
for s in 0 1 2; do
  [ -f outputs/m6_s${s}_S/best.pt ] && [ -n "$(grep -l 'best val recall' outputs/run_m6_s${s}_S.log 2>/dev/null)" ] && continue
  until [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2500 ]; do sleep 60; done  # free GPU
  timeout 2h $PY -I train.py --model 6 --seed $s --steps 20000 --eval-every 1000 --workers 12 --tag _S --wide-scat > outputs/run_m6_s${s}_S.log 2>&1
  echo "m6 s$s S exit $? $(date +%H:%M) $(tail -1 outputs/run_m6_s${s}_S.log)" >> outputs/run_wide_scat.log
done
(cd ../02_benchmark && $PY -I tau_sweep.py --runs m6_s0_S,m6_s1_S,m6_s2_S) > outputs/tau_sweep_S.log 2>&1
echo "sweep exit $? $(date +%H:%M)" >> outputs/run_wide_scat.log
(cd ../02_benchmark && $PY -I variants_eval.py) > outputs/variants_eval_S.log 2>&1
echo "eval exit $? $(date +%H:%M)" >> outputs/run_wide_scat.log
