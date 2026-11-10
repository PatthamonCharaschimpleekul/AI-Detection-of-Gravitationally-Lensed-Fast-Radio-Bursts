"""Run the two steps that read raw dynamic spectra without keeping the 13 GB on disk.

Each repeater file is downloaded just before the step opens it and deleted once it is
closed, with a bounded number fetched ahead. The steps themselves run unchanged, so their
output should match a run on fully downloaded data. Files reopened later are fetched again.

Usage: python stream_preprocess.py [data_dir] [--ahead 40] [--workers 6] [--limit N]
         runs preprocess_catalog2.py (needs data_dir/chimefrbcat2.csv)
       python stream_preprocess.py [data_dir] --cache
         runs inject.build_cache() in 02_injection_labelling/01_injection (needs the preproc output)
"""
import csv
import runpy
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import h5py

import subprocess
import time

from download_catalog2 import BASE, is_complete


def fetch(url, dest, tries=20):
    """curl with a hard time limit per attempt: urllib can hang on a server that trickles bytes."""
    if dest.exists() and is_complete(dest):
        return "skip"
    tmp = dest.with_name(dest.name + ".part")
    for attempt in range(tries):
        r = subprocess.run(["curl", "-sSfL", "--max-time", "180", "--speed-limit", "20000", "--speed-time", "30",
                            "-o", str(tmp), url], capture_output=True)
        if r.returncode == 0 and is_complete(tmp):
            tmp.replace(dest)
            return "ok"
        tmp.unlink(missing_ok=True)
        time.sleep(min(3 * 2 ** attempt, 120))
    return f"curl failed: {r.returncode} {r.stderr.decode()[-120:]}"

HERE = Path(__file__).parent
args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and not sys.argv[i - 1].startswith("--")]
opt = lambda k, v: int(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else v
AHEAD, WORKERS, LIMIT = opt("--ahead", 40), opt("--workers", 6), opt("--limit", 0)
d = Path(args[0]) if args else HERE / "data" / "catalog2"
ds = d / "dynamic_spectra"
ds.mkdir(parents=True, exist_ok=True)

CACHE_MODE = "--cache" in sys.argv
if CACHE_MODE:  # build_cache reads files in preproc order and skips coarse-dt ones
    with h5py.File(d / "preproc" / "repeaters_256x160.h5") as f:
        names = [t for t, c in zip(f["meta/tns"][:].astype(str), f["meta/coarse_dt"][:]) if not c]
else:
    with open(d / "chimefrbcat2.csv", newline="") as f:
        names = sorted({r["tns_name"] for r in csv.DictReader(f) if r["repeater_name"] not in ("", "-9999")})
names = names[:LIMIT] if LIMIT else names
path_of = lambda n: ds / f"{n}_stokesi_dynamic_spectrum.h5"
url_of = lambda n: f"{BASE}/dynamic_spectra/data/{n}_stokesi_dynamic_spectrum.h5"
slots = threading.Semaphore(AHEAD)
futures, lock = {}, threading.Lock()
failed = []


def prefetch(n):
    slots.acquire()
    status = fetch(url_of(n), path_of(n))
    if status not in ("ok", "skip"):
        failed.append((n, status))
    return status


pool = ThreadPoolExecutor(WORKERS)
for n in names:
    futures[n] = pool.submit(prefetch, n)


class StreamFile(h5py.File):
    """h5py.File that fetches a missing dynamic spectrum first and deletes it on close."""

    def __init__(self, name, *a, **k):
        p = Path(name)
        # Only the preprocessing reads, which run on the main thread. fetch() also opens files
        # through h5py to check them (.part files, and finished files on worker threads).
        self._stream = (threading.current_thread() is threading.main_thread()
                        and p.name.endswith("_stokesi_dynamic_spectrum.h5") and p.parent.resolve() == ds.resolve())
        if self._stream:
            n = p.name.replace("_stokesi_dynamic_spectrum.h5", "")
            with lock:
                fut = futures.pop(n, None)
            # A prefetched file holds a slot until it is closed, even if the prefetch failed.
            self._owned_slot = fut is not None
            if fut is not None:
                fut.result()
            if not p.exists():
                status = fetch(url_of(n), p)
                if status not in ("ok", "skip"):
                    raise OSError(f"could not fetch {n}: {status}")
            self._path = p
        super().__init__(name, *a, **k)

    def __exit__(self, *exc):
        out = super().__exit__(*exc)
        if self._stream:
            self._path.unlink(missing_ok=True)
            if self._owned_slot:
                slots.release()
        return out


h5py.File = StreamFile
try:
    if CACHE_MODE:
        sys.path.insert(0, str(HERE.parents[1] / "02_injection_labelling" / "01_injection"))
        import inject
        assert inject.REAL.resolve() == d.resolve(), "build_cache reads its own data path"
        inject.build_cache()
    else:
        sys.argv = [str(HERE / "preprocess_catalog2.py"), str(d)] + (["--limit", str(LIMIT)] if LIMIT else [])
        runpy.run_path(str(HERE / "preprocess_catalog2.py"), run_name="__main__")
finally:
    pool.shutdown(wait=False, cancel_futures=True)  # a worker may be blocked on a slot
    for n in names:  # files fetched ahead but never opened
        path_of(n).unlink(missing_ok=True)
    if failed:
        print("fetch failures:", failed)
