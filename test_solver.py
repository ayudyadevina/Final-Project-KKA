import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from heuristics import build_ikatan, select_var, order_values
from propagation import forward_check, restore

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
            solve(csp, Config(ac3=True))

    def test_failure_semua_varian(self):
        for nama, cfg in VARIAN.items():
            if cfg.ac3:
                continue
            with self.subTest(varian=nama):
                csp = CSP([kelas("X-A", "D1", grup="A"), kelas("Y-B", "D1", grup="B")], R, [Slot("S1", "Senin", "7:00")])
                asg, st = solve(csp, cfg)
                self.assertIsNone(asg)
                self.assertEqual(st["status"], "failure")

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
        
    def test_semua_varian_valid_s1(self):
        for nama, cfg in VARIAN.items():
            if cfg.ac3:
                continue
            with self.subTest(varian=nama):
                csp = muat_csp(S1)
                asg, st = solve(csp, replace(cfg, timeout=60))
                self.assertEqual(st["status"], "solved", st)
                with tempfile.TemporaryDirectory() as d:
                    f = Path(d) / "jadwal.csv"
                    simpan_jadwal(asg, f)
                    self.assertEqual(verifikasi(load_jadwal_csv(f), S1), [])

    def test_seed_reproducible(self):
        cfg = replace(VARIAN["BT"], seed=42, timeout=60)
        _, a = solve(muat_csp(S1), cfg)
        _, b = solve(muat_csp(S1), cfg)
        self.assertEqual((a["nodes"], a["backtracks"], a["checks"]),
                        (b["nodes"], b["backtracks"], b["checks"]))

class TestHeuristik(unittest.TestCase):
    def test_baseline_urutan_tetap(self):
        a, b = kelas("A-A", "D1", grup="A"), kelas("B-B", "D2", grup="B")
        domains = {a: [1, 2, 3], b: [1]}
        v = select_var([a, b], {}, domains, build_ikatan([a, b]), Config())
        self.assertIs(v, a)

    def test_mrv_pilih_domain_terkecil(self):
        a, b = kelas("A-A", "D1", grup="A"), kelas("B-B", "D2", grup="B")
        domains = {a: [1, 2, 3], b: [1]}
        v = select_var([a, b], {}, domains, build_ikatan([a, b]), Config(mrv=True))
        self.assertIs(v, b)

    def test_degree_pecah_seri(self):
        a = kelas("A-A", "D1;D2", grup="A")      # terikat ke b (D1) dan c (D2)
        b = kelas("B-B", "D1", grup="B")
        c = kelas("C-C", "D2", grup="C")
        d = kelas("D-D", "D9", grup="D")         # tidak terikat siapa pun
        order = [d, b, c, a]
        domains = {k: [1, 2] for k in order}     # semua seri di MRV
        v = select_var(order, {}, domains, build_ikatan(order), Config(mrv=True, degree=True))
        self.assertIs(v, a)

    def test_lcv_tetangga_tidak_terikat(self):
        x, y = kelas("X-A", "D1", grup="A"), kelas("Y-B", "D2", grup="B")
        domains = {x: [("S1", "R1"), ("S3", "R9")], y: [("S1", "R1"), ("S2", "R2")]}
        urut = order_values(x, [x, y], {}, domains, build_ikatan([x, y]), Config(mrv=True, lcv=True))
        self.assertEqual(urut, [("S3", "R9"), ("S1", "R1")])   # S1/R1 menutup 1 nilai y

    def test_lcv_tetangga_terikat(self):
        x, y = kelas("X-A", "D1", grup="A"), kelas("Y-B", "D1", grup="B")   # sedosen
        domains = {x: [("S1", "R1"), ("S2", "R9"), ("S4", "R1")], y: [("S1", "R2"), ("S1", "R3"), ("S2", "R2")]}
        urut = order_values(x, [x, y], {}, domains, build_ikatan([x, y]), Config(mrv=True, lcv=True))
        # S1 menutup 2 nilai y, S2 menutup 1, S4 menutup 0
        self.assertEqual([s for s, _ in urut], ["S4", "S2", "S1"])


class TestForwardChecking(unittest.TestCase):
    def test_hapus_lalu_restore(self):
        a, b = kelas("A-A", "D1", grup="A"), kelas("B-B", "D1", grup="B")
        csp = CSP([a, b], R, [Slot("S1", "Senin", "7:00"), Slot("S2", "Senin", "10:00")])
        domains = {k: list(d) for k, d in csp.domains.items()}
        awal_b = set(domains[b])
        val = domains[a][0]
        removed = forward_check(csp, a, val, {}, domains)
        self.assertIsNotNone(removed)
        # sedosen: seluruh slot val[0] hilang dari domain b
        self.assertTrue(all(s != val[0] for s, _ in domains[b]))
        restore(domains, removed)
        self.assertEqual(set(domains[b]), awal_b)

    def test_wipeout_memulihkan_domain(self):
        a, b = kelas("A-A", "D1", grup="A"), kelas("B-B", "D1", grup="B")
        csp = CSP([a, b], R, [Slot("S1", "Senin", "7:00")])    # hanya 1 slot
        domains = {k: list(d) for k, d in csp.domains.items()}
        awal_b = set(domains[b])
        hasil = forward_check(csp, a, domains[a][0], {}, domains)
        self.assertIsNone(hasil)
        self.assertEqual(set(domains[b]), awal_b)


if __name__ == "__main__":
    unittest.main(verbosity=2)