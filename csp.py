import csv
from dataclasses import dataclass
from pathlib import Path

BASE = Path(__file__).parent


@dataclass(frozen=True)
class Kelas:
    id: str
    nama: str
    semester: int
    grup: str             
    sks: int
    dosen: frozenset      
    tipe: str             


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
        return [(s, r) for s in slot for r in ruang if r.tipe == k.tipe]

    def _build_neighbors(self, kelas):
        return {k: [o for o in kelas if o != k] for k in kelas}

    def conflict(self, a, va, b, vb):
        """True kalau a=va dan b=vb melanggar constraint."""
        self.constraint_checks += 1
        slot_a, ruang_a = va
        slot_b, ruang_b = vb
        if slot_a != slot_b:
            return False                
        if ruang_a == ruang_b:          
            return True
        if a.dosen & b.dosen:           
            return True
        if a.semester == b.semester and a.grup == b.grup:    
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