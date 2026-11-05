"""Download CHIME/FRB Catalog 2 repeater dynamic spectra and the exposure file.

Resumable: files that already exist and open as HDF5 are skipped; truncated ones are fetched again.
Usage: python -I download_catalog2.py [--workers 8]
"""
import argparse
import csv
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import h5py

BASE = "https://www.canfar.net/storage/vault/file/AstroDataCitationDOI/CISTI.CANFAR/25.0066/data"
HERE = Path(__file__).parent
OUT = HERE / "data" / "catalog2"


def is_complete(path):
    """True only if the file opens as HDF5; a dropped connection can leave a valid header on a truncated file."""
    try:
        with h5py.File(path, "r"):
            return True
    except OSError:
        return False


def fetch(url, dest, tries=4):
    if dest.exists() and is_complete(dest):
        return "skip"
    tmp = dest.with_suffix(".part")
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=300) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            if is_complete(tmp):
                tmp.replace(dest)
                return "ok"
            err = "truncated or not hdf5"  # CANFAR sometimes ends the stream early or returns an HTML page
        except urllib.error.HTTPError as e:  # a real answer from the server: do not retry
            tmp.unlink(missing_ok=True)
            return f"http {e.code}"
        except OSError as e:  # dropped connection, timeout, reset: retry with backoff
            err = f"network: {type(e).__name__}"
        tmp.unlink(missing_ok=True)
        if attempt < tries - 1:
            time.sleep(5 * 2 ** attempt)
    return err


def repeater_bursts(table):
    with open(table, newline="") as f:
        names = {row["tns_name"] for row in csv.DictReader(f) if row["repeater_name"] not in ("", "-9999")}
    return sorted(names)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    ds = OUT / "dynamic_spectra"
    ds.mkdir(parents=True, exist_ok=True)
    print("exposure:", fetch(f"{BASE}/exposure/chimefrbcat2_exposure.h5", OUT / "chimefrbcat2_exposure.h5"), flush=True)

    names = repeater_bursts(OUT / "chimefrbcat2.csv")
    jobs = {n: (f"{BASE}/dynamic_spectra/data/{n}_stokesi_dynamic_spectrum.h5", ds / f"{n}_stokesi_dynamic_spectrum.h5") for n in names}
    with ThreadPoolExecutor(args.workers) as pool:
        results = dict(zip(jobs, pool.map(lambda j: fetch(*j), jobs.values())))

    failed = {n: s for n, s in results.items() if s not in ("ok", "skip")}
    (OUT / "missing_dynamic_spectra.txt").write_text("".join(f"{n}\t{s}\n" for n, s in sorted(failed.items())))
    print(f"{len(names)} repeater bursts: {sum(s == 'ok' for s in results.values())} downloaded, "
          f"{sum(s == 'skip' for s in results.values())} already present, {len(failed)} failed (see missing_dynamic_spectra.txt)")


if __name__ == "__main__":
    main()
