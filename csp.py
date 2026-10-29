"""
csp.py - Model CSP penjadwalan kuliah.

Variabel   : tiap Kelas
Domain     : pasangan (Slot, Ruang) yang lolos filter unary
             U1: tipe ruang harus sama dengan tipe kelas (teori/lab)
Constraint : C1 ruang+slot sama dilarang
             C2 ada dosen yang sama di slot sama dilarang
             C3 semester sama DAN huruf kelas sama di slot sama dilarang
                (mahasiswa satu kelas mengambil semua MK di huruf kelas itu)

Asumsi: satu kelas menempati satu slot (sks diabaikan).
"""
import csv
from dataclasses import dataclass
from pathlib import Path

BASE = Path(__file__).parent


@dataclass(frozen=True)
class Kelas:
    id: str
    nama: str
    semester: int
    grup: str             # huruf kelas (A, B, ...), kolom "kelas" di CSV
    sks: int
    dosen: frozenset      # bisa lebih dari satu dosen (dipisah ';' di CSV)
    tipe: str             # "teori" / "lab"


@dataclass(frozen=True)
class Ruang:
    id: str
    tipe: str


@dataclass(frozen=True)
class Slot:
    id: str
    hari: str
    mulai: str


def _read(path):
    # utf-8-sig membuang BOM yang kadang muncul di CSV dari Excel/Sheets
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_data(kelas_csv, ruang_csv, slot_csv):
    kelas = [Kelas(r["id_kelas"], r["nama_mk"], int(r["semester"]),
                   r["kelas"], int(r["sks"]), frozenset(r["dosen"].split(";")), r["tipe"])
             for r in _read(kelas_csv)]
    ruang = [Ruang(r["id_ruang"], r["tipe"]) for r in _read(ruang_csv)]
    slot = [Slot(r["id_slot"], r["hari"], r["mulai"]) for r in _read(slot_csv)]
    return kelas, ruang, slot


class CSP:
    def __init__(self, kelas, ruang, slot):
        self.variables = list(kelas)
        self.constraint_checks = 0
        self.domains = {k: self._build_domain(k, ruang, slot) for k in kelas}
        self.neighbors = self._build_neighbors(kelas)

    def _build_domain(self, k, ruang, slot):
        # U1: tipe ruang cocok dengan tipe kelas
        return [(s, r) for s in slot for r in ruang if r.tipe == k.tipe]

    def _build_neighbors(self, kelas):
        # C1 berlaku untuk semua pasangan kelas, jadi semua kelas bertetangga
        return {k: [o for o in kelas if o != k] for k in kelas}

    def conflict(self, a, va, b, vb):
        """True kalau a=va dan b=vb melanggar constraint."""
        self.constraint_checks += 1
        slot_a, ruang_a = va
        slot_b, ruang_b = vb
        if slot_a != slot_b:
            return False                # beda slot, aman
        if ruang_a == ruang_b:          # C1
            return True
        if a.dosen & b.dosen:           # C2
            return True
        if a.semester == b.semester and a.grup == b.grup:    # C3
            return True
        return False


if __name__ == "__main__":
    kelas, ruang, slot = load_data(
        BASE / "data" / "kelas.csv",
        BASE / "data" / "ruang.csv",
        BASE / "data" / "slot.csv",
    )
    csp = CSP(kelas, ruang, slot)
    print(f"kelas={len(kelas)} ruang={len(ruang)} slot={len(slot)}")
    sizes = [len(d) for d in csp.domains.values()]
    print("domain min/max:", min(sizes), max(sizes))
    for k in kelas[:3]:
        print(k.id, sorted(k.dosen), k.tipe, "| domain:", len(csp.domains[k]))
    a, b = kelas[0], kelas[1]
    v = csp.domains[a][0]
    print("conflict nilai sama persis:", csp.conflict(a, v, b, v))
    print("constraint_checks:", csp.constraint_checks)