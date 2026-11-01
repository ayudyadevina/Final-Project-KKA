import argparse
import csv
import random
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional
from csp import CSP, load_data
from heuristics import build_ikatan, select_var, order_values
from propagation import forward_check, restore, mac, ac3_awal
BASE = Path(__file__).parent

@dataclass
class Config:
    mrv: bool = False
    degree: bool = False        
    lcv: bool = False
    fc: bool = False
    ac3: bool = False          
    timeout: float = 60.0       
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

def solve(csp, config=None):
    config = config or Config()
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
    if config.ac3 and ac3_awal(csp, domains, ikatan) is None:
        stats.update(time=time.perf_counter() - t0, checks=csp.constraint_checks, status="failure")
        return None, stats

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
            if config.ac3:
                removed = mac(csp, var, val, assignment, domains, ikatan)
                if removed is None:
                    continue
            elif config.fc:
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
