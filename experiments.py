import argparse
import csv
import statistics
import tracemalloc
from dataclasses import replace
from pathlib import Path

from main import PILIHAN_ALGO
from solver import VARIAN, solve, muat_csp
from verify import verifikasi

FOLDER_PROYEK = Path(__file__).parent
FOLDER_DATA = FOLDER_PROYEK / "data"
KOLOM_CSV = ["skenario", "varian", "run", "status", "waktu", "nodes", "backtracks", "checks", "memori_kb", "valid"]
KOLOM_RINGKASAN = ["skenario", "varian", "run", "solved", "timeout", "failure", "valid",
                   "waktu_rata2", "waktu_std", "nodes_rata2", "backtracks_rata2", "checks_rata2", "memori_kb"]


def hitung_memori(csp, konfig):
    tracemalloc.start()
    try:
        solve(csp, konfig)
        _, memori_puncak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return memori_puncak / 1024


def buat_ringkasan(berkas_hasil, berkas_ringkasan, runs_diharapkan):
    with open(berkas_hasil, newline="", encoding="utf-8") as f:
        baris_semua = list(csv.DictReader(f))

    urut_varian = {nama: i for i, nama in enumerate(VARIAN)}
    kelompok = {}
    for b in baris_semua:
        kelompok.setdefault((b["skenario"], b["varian"]), []).append(b)

    ringkas = []
    for (skenario, varian), rows in sorted(kelompok.items(),
                                           key=lambda kv: (kv[0][0], urut_varian.get(kv[0][1], 99))):
        waktu = [float(r["waktu"]) for r in rows]
        memori = [float(r["memori_kb"]) for r in rows if r["memori_kb"] != ""]
        ringkas.append({
            "skenario": skenario, "varian": varian, "run": len(rows),
            "solved": sum(r["status"] == "solved" for r in rows),
            "timeout": sum(r["status"] == "timeout" for r in rows),
            "failure": sum(r["status"] == "failure" for r in rows),
            "valid": sum(r["valid"] == "True" for r in rows),
            "waktu_rata2": round(statistics.mean(waktu), 3),
            "waktu_std": round(statistics.stdev(waktu), 3) if len(waktu) > 1 else 0.0,
            "nodes_rata2": round(statistics.mean(int(r["nodes"]) for r in rows), 1),
            "backtracks_rata2": round(statistics.mean(int(r["backtracks"]) for r in rows), 1),
            "checks_rata2": round(statistics.mean(int(r["checks"]) for r in rows), 1),
            "memori_kb": memori[0] if memori else "",
        })

    with open(berkas_ringkasan, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KOLOM_RINGKASAN, lineterminator="\n")
        w.writeheader()
        w.writerows(ringkas)

    print(f"\nRingkasan ({berkas_ringkasan}):")
    print(f"{'skenario':8} {'varian':22} {'run':>3} {'solved':>6} {'timeout':>7} {'waktu_rata2':>11} {'nodes_rata2':>11}")
    for r in ringkas:
        print(f"{r['skenario']:8} {r['varian']:22} {r['run']:>3} {r['solved']:>6} {r['timeout']:>7} "
              f"{r['waktu_rata2']:>11.3f} {r['nodes_rata2']:>11.1f}")

    masalah = []
    for r in ringkas:
        if r["run"] != runs_diharapkan:
            masalah.append(f"{r['skenario']} {r['varian']}: {r['run']} run (harusnya {runs_diharapkan})")
        if r["solved"] != r["valid"]:
            masalah.append(f"{r['skenario']} {r['varian']}: ada jadwal solved yang TIDAK valid")
        if r["skenario"] == "S3" and r["solved"] > 0:
            masalah.append(f"S3 {r['varian']}: solved padahal S3 mustahil, cek model/dataset")
    ada = {r["varian"] for r in ringkas}
    for nama in VARIAN:
        if nama not in ada:
            masalah.append(f"varian '{nama}' belum ada di hasil")
    print("\nCek konsistensi eksperimen:")
    if masalah:
        print("\n".join(f"  ! {m}" for m in masalah))
    else:
        print("Semua pengecekan konsistensi data lolos.")
    print("\nCatatan timeout:")
    ada_timeout = False
    for r in ringkas:
        if r["timeout"] > 0:
            ada_timeout = True
            print(
                f"  ! {r['skenario']} {r['varian']}: "
                f"{r['timeout']} dari {r['run']} run mengalami timeout."
            )
    if not ada_timeout:
        print("Tidak ada timeout.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skenario", nargs="+", default=["S1", "S2", "S3"])
    parser.add_argument("--algo", nargs="+", default=list(PILIHAN_ALGO), choices=list(PILIHAN_ALGO),
                        help="kode varian seperti di main.py (default: semua)")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--out", default=str(FOLDER_PROYEK / "hasil" / "hasil.csv"))
    parser.add_argument("--append", action="store_true",
                        help="tambahkan ke file yang sudah ada (tanpa menimpa)")
    parser.add_argument("--tanpa-memori", action="store_true", help="lewati pengukuran memori")
    args = parser.parse_args()

    berkas_out = Path(args.out)
    berkas_out.parent.mkdir(parents=True, exist_ok=True)
    tulis_header = not (args.append and berkas_out.exists() and berkas_out.stat().st_size > 0)

    with open(berkas_out, "a" if args.append else "w", newline="", encoding="utf-8") as berkas:
        penulis = csv.DictWriter(berkas, fieldnames=KOLOM_CSV, lineterminator="\n")
        if tulis_header:
            penulis.writeheader()
        for skenario in args.skenario:
            folder = FOLDER_DATA / skenario
            if not folder.exists():
                print(f"Folder {folder} tidak ada. Jalankan make_datasets.py dulu.")
                return
            csp = muat_csp(folder)
            for kode in args.algo:
                nama_varian = PILIHAN_ALGO[kode]
                konfig_dasar = VARIAN[nama_varian]
                for run_ke in range(1, args.runs + 1):
                    konfig = replace(konfig_dasar, timeout=args.timeout, seed=run_ke)
                    jadwal_hasil, stat = solve(csp, konfig)
                    lolos = ""
                    if jadwal_hasil:
                        jadwal_id = {kls.id: (slot_kelas.id, rng.id)
                                     for kls, (slot_kelas, rng) in jadwal_hasil.items()}
                        lolos = len(verifikasi(jadwal_id, folder)) == 0
                    memori = ""
                    if run_ke == 1 and not args.tanpa_memori:
                        memori = round(hitung_memori(csp, konfig), 1)
                    penulis.writerow({"skenario": skenario, "varian": nama_varian, "run": run_ke,
                                      "status": stat["status"], "waktu": round(stat["time"], 4),
                                      "nodes": stat["nodes"], "backtracks": stat["backtracks"],
                                      "checks": stat["checks"], "memori_kb": memori, "valid": lolos})
                    berkas.flush()
                    print(skenario, nama_varian, run_ke, stat["status"], round(stat["time"], 3), flush=True)

    print(f"\nTersimpan: {berkas_out}")
    buat_ringkasan(berkas_out, berkas_out.with_name("ringkasan.csv"), args.runs)


if __name__ == "__main__":
    main()
