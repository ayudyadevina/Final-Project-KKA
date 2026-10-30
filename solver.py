"""
solver.py - Backtracking search untuk CSP penjadwalan.

Antarmuka: assignment, stats = solve(csp, Config(...))

assignment : {Kelas: (Slot, Ruang)} bila solved, None bila failure/timeout
stats      : nodes, backtracks, checks, time, status ("solved"/"failure"/"timeout")

Flag: mrv, degree (pemecah seri MRV), lcv, fc. ac3 belum ada (task 14, PIC A).
"""

import argparse
import csv
import random
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from csp import CSP, load_data
from heuristics import build_ikatan, select_var, order_values
from propagation import forward_check, restore

BASE = Path(__file__).parent


@dataclass
class Config:
    mrv: bool = False
    degree: bool = False        # pemecah seri MRV
    lcv: bool = False
    fc: bool = False
    ac3: bool = False           # MAC
    timeout: float = 60.0       # detik
    seed: Optional[int] = None  

VARIAN = {
    "BT": Config(),
    "BT + MRV (+degree)": Config(mrv=True, degree=True),
    "BT + MRV + LCV": Config(mrv=True, degree=True, lcv=True),
    "BT + MRV + FC": Config(mrv=True, degree=True, fc=True),
    "BT + MAC (AC-3)": Config(ac3=True),
}


class _Timeout(Exception):
    pass


def _cek_didukung(config):
    if config.ac3:
        raise NotImplementedError("ac3/MAC belum diimplementasikan (task 14, PIC A).")


def solve(csp, config=None):
    config = config or Config()
    _cek_didukung(config)

    order = list(csp.variables)
    domains = {k: list(csp.domains[k]) for k in order}
    if config.seed is not None:
        rng = random.Random(config.seed)
        rng.shuffle(order)
        for d in domains.values():
            rng.shuffle(d)
    ikatan = build_ikatan(order)

    csp.constraint_checks = 0
    stats = {"nodes": 0, "backtracks": 0}
    assignment = {}
    t0 = time.perf_counter()
    deadline = t0 + config.timeout

    def consistent(var, val):
        return not any(csp.conflict(var, val, o, v) for o, v in assignment.items())

    def backtrack():
        if len(assignment) == len(order):
            return True
        var = select_var(order, assignment, domains, ikatan, config)
        for val in order_values(var, order, assignment, domains, ikatan, config):
            if time.perf_counter() >= deadline:
                raise _Timeout
            removed = None
            if config.fc:
                removed = forward_check(csp, var, val, assignment, domains)
                if removed is None:
                    continue
            elif not consistent(var, val):
                continue
            assignment[var] = val
            stats["nodes"] += 1
            if backtrack():
                return True
            del assignment[var]
            if removed is not None:
                restore(domains, removed)
        stats["backtracks"] += 1
        return False

    try:
        ok = backtrack()
        status = "solved" if ok else "failure"
    except _Timeout:
        ok, status = False, "timeout"

    stats["time"] = time.perf_counter() - t0
    stats["checks"] = csp.constraint_checks
    stats["status"] = status
    return (dict(assignment) if ok else None), stats


def simpan_jadwal(assignment, path):
    """Tulis jadwal ke CSV format verify.py: id_kelas,id_slot,id_ruang."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id_kelas", "id_slot", "id_ruang"])
        for k, (s, r) in assignment.items():
            w.writerow([k.id, s.id, r.id])


def muat_csp(data_dir):
    data_dir = Path(data_dir)
    kelas, ruang, slot = load_data(data_dir / "kelas.csv", data_dir / "ruang.csv", data_dir / "slot.csv")
    return CSP(kelas, ruang, slot)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=str(BASE / "data" / "S1"))
    p.add_argument("--algo", default="BT", choices=list(VARIAN))
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--out", default=str(BASE / "hasil" / "jadwal.csv"))
    a = p.parse_args()

    csp = muat_csp(a.data)
    cfg = replace(VARIAN[a.algo], timeout=a.timeout, seed=a.seed)
    asg, st = solve(csp, cfg)
    print(f"{a.algo} | {len(csp.variables)} kelas | " + " ".join(f"{k}={v:.3f}" if k == "time" else f"{k}={v}" for k, v in st.items()))
    if asg:
        simpan_jadwal(asg, a.out)
        print(f"Jadwal disimpan: {a.out}")
        print(f"Cek: python verify.py {a.out} --data {a.data}")