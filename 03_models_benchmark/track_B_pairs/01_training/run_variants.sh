#!/bin/sh
# Source-memorisation variants of model 6 (plan 2026-11-10_1300): M, P, M+P x seeds 0-2, then the evaluation.
cd "$(dirname "$0")"
PY=../../../venv/Scripts/python
for v in M P MP; do
  case $v in M) F="--merge-unrelated";; P) F="--bandpass";; MP) F="--merge-unrelated --bandpass";; esac
  for s in 0 1 2; do
    [ -f outputs/m6_s${s}_$v/best.pt ] && [ -n "$(grep -l 'best val recall' outputs/run_m6_s${s}_$v.log 2>/dev/null)" ] && continue
    until [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2500 ]; do sleep 60; done  # free GPU (Ollama OOM, 2026-11-08)
    timeout 2h $PY -I train.py --model 6 --seed $s --steps 20000 --eval-every 1000 --workers 12 --tag _$v $F > outputs/run_m6_s${s}_$v.log 2>&1
    echo "m6 s$s $v exit $? $(date +%H:%M) $(tail -1 outputs/run_m6_s${s}_$v.log)" >> outputs/run_variants.log
  done
done
(cd ../02_benchmark && $PY -I variants_eval.py) > outputs/variants_eval.log 2>&1
echo "eval exit $? $(date +%H:%M)" >> outputs/run_variants.log
