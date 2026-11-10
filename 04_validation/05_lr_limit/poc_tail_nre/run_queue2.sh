#!/bin/sh
# Follow-up to run_queue.sh, added after 60k steps beat every 30k method on recall.
# Asks: does more training close the gap to exact, and does the hard-negative gain survive it?
# Kept separate because a shell reads a running script as it goes, so run_queue.sh can't be edited.
until grep -q 'queue finished' outputs/logs/queue.log; do sleep 120; done
run() { # method seed finite steps width
  name="$1_w$5_s$4"; [ "$3" != 0 ] && name="${name}_finite$3"; name="${name}_seed$2"
  [ -f "outputs/runs/$name/meta.json" ] && { echo "skip $name"; return; }
  echo "start $name $(date +%H:%M)"
  python train.py --method "$1" --seed "$2" --finite "$3" --steps "$4" --width "$5" > "outputs/logs/$name.log" 2>&1 || echo "FAILED $name"
}
for m in naive iw cond; do run $m 0 0 60000 48; done
run plain 0 0 120000 48
echo "queue2 finished $(date +%H:%M)"
