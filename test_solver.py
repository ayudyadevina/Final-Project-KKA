"""
Jalankan: python test_solver.py   (atau: pytest test_solver.py)

Validasi jadwal memakai verify.py (independen dari csp.py / solver.py).
Tes data asli butuh data/S1 (hasil: python make_datasets.py).
"""
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from csp import CSP, Kelas, Ruang, Slot
from solver import Config, VARIAN, solve, simpan_jadwal, muat_csp
from verify import verifikasi, load_jadwal_csv

BASE = Path(__file__).parent
S1 = BASE / "data" / "S1"


def kelas(id_, dosen, sem=3, grup="A", tipe="teori"):
    return Kelas(id_, id_, sem, grup, 3, frozenset(dosen.split(";")), tipe)


R = [Ruang("R1", "teori"), Ruang("R2", "teori")]


class TestKecil(unittest.TestCase):
    def test_solved(self):
        # 2 kelas sedosen, 2 slot -> harus beda slot
        csp = CSP([kelas("X-A", "D1", grup="A"), kelas("Y-B", "D1", grup="B")],
                R, [Slot("S1", "Senin", "7:00"), Slot("S2", "Senin", "10:00")])
        asg, st = solve(csp, Config())
        self.assertEqual(st["status"], "solved")
        self.assertEqual(len(asg), 2)
        slots = {s.id for s, _ in asg.values()}
        self.assertEqual(len(slots), 2)

    def test_failure(self):
        # 2 kelas sedosen, hanya 1 slot -> mustahil
        csp = CSP([kelas("X-A", "D1", grup="A"), kelas("Y-B", "D1", grup="B")],
                R, [Slot("S1", "Senin", "7:00")])
        asg, st = solve(csp, Config())
        self.assertIsNone(asg)
        self.assertEqual(st["status"], "failure")
        self.assertGreater(st["backtracks"], 0)

    def test_semester_dan_grup_sama(self):
        # C3: sem sama + grup sama, dosen beda, 1 slot -> mustahil
        csp = CSP([kelas("X-A", "D1"), kelas("Y-A", "D2")], R,
                [Slot("S1", "Senin", "7:00")])
        _, st = solve(csp, Config())
        self.assertEqual(st["status"], "failure")

    def test_timeout(self):
        csp = CSP([kelas("X-A", "D1")], R, [Slot("S1", "Senin", "7:00")])
        asg, st = solve(csp, Config(timeout=0.0))
        self.assertIsNone(asg)
        self.assertEqual(st["status"], "timeout")

    def test_flag_belum_ada(self):
        csp = CSP([kelas("X-A", "D1")], R, [Slot("S1", "Senin", "7:00")])
        with self.assertRaises(NotImplementedError):
            solve(csp, Config(mrv=True))

    def test_domain_asli_tidak_berubah(self):
        csp = CSP([kelas("X-A", "D1")], R, [Slot("S1", "Senin", "7:00")])
        sebelum = {k: list(d) for k, d in csp.domains.items()}
        solve(csp, Config(seed=1))
        self.assertEqual(sebelum, csp.domains)

    def test_nama_varian_lengkap(self):
        self.assertEqual(len(VARIAN), 5)


@unittest.skipUnless(S1.exists(), "data/S1 belum ada (jalankan make_datasets.py)")
class TestS1(unittest.TestCase):
    def test_bt_s1_valid(self):
        csp = muat_csp(S1)
        asg, st = solve(csp, Config(timeout=60))
        self.assertEqual(st["status"], "solved", st)
        self.assertEqual(len(asg), len(csp.variables))
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "jadwal.csv"
            simpan_jadwal(asg, f)
            pelanggaran = verifikasi(load_jadwal_csv(f), S1)
        self.assertEqual(pelanggaran, [], pelanggaran[:5])

    def test_seed_reproducible(self):
        cfg = replace(VARIAN["BT"], seed=42, timeout=60)
        _, a = solve(muat_csp(S1), cfg)
        _, b = solve(muat_csp(S1), cfg)
        self.assertEqual((a["nodes"], a["backtracks"], a["checks"]),
                        (b["nodes"], b["backtracks"], b["checks"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)