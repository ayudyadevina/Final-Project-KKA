import csv
import statistics
import tracemalloc
from dataclasses import replace
from pathlib import Path
from solver import VARIAN, solve, muat_csp
from verify import verifikasi

FOLDER_PROYEK = Path(__file__).parent
FOLDER_DATA = FOLDER_PROYEK / "data"
DAFTAR_SKENARIO = ["S1", "S2", "S3"]
JUMLAH_RUN = 5
BATAS_WAKTU = 60
KOLOM_CSV = ["skenario", "varian", "run", "status", "waktu", "nodes", "backtracks", "checks", "memori_kb", "valid"]

def hitung_memori(csp, konfig):
    tracemalloc.start()
    solve(csp, konfig)
    _, memori_puncak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return memori_puncak / 1024

def main():
    hasil = []
    folder_hasil = FOLDER_PROYEK / "hasil"
    folder_hasil.mkdir(exist_ok=True)
    with open(folder_hasil / "hasil.csv", "w", newline="") as berkas:
        penulis = csv.DictWriter(berkas, fieldnames=KOLOM_CSV)
        penulis.writeheader()
        for skenario in DAFTAR_SKENARIO:
            folder = FOLDER_DATA / skenario
            csp = muat_csp(folder)
            for nama_varian, konfig_dasar in VARIAN.items():
                for run_ke in range(1, JUMLAH_RUN + 1):
                    konfig = replace(konfig_dasar, timeout=BATAS_WAKTU, seed=run_ke)
                    try:
                        jadwal_hasil, stat = solve(csp, konfig)
                    except NotImplementedError:
                        print(f"{skenario} {nama_varian}: belum diimplementasi, dilewati")
                        break
                    lolos = ""
                    if jadwal_hasil:
                        jadwal_id = {kls.id: (slot_kelas.id, rng.id) for kls, (slot_kelas, rng) in jadwal_hasil.items()}
                        lolos = len(verifikasi(jadwal_id, folder)) == 0
                    memori = round(hitung_memori(csp, konfig), 1) if run_ke == 1 else ""
                    baris = {"skenario": skenario, "varian": nama_varian, "run": run_ke,
                             "status": stat["status"], "waktu": round(stat["time"], 4),
                             "nodes": stat["nodes"], "backtracks": stat["backtracks"],
                             "checks": stat["checks"], "memori_kb": memori, "valid": lolos}
                    hasil.append(baris)
                    penulis.writerow(baris)
                    berkas.flush()
                    print(skenario, nama_varian, run_ke, stat["status"], round(stat["time"], 3))

    print("\nrata-rata waktu (detik):")
    for skenario in DAFTAR_SKENARIO:
        for nama_varian in VARIAN:
            daftar_waktu = [baris["waktu"] for baris in hasil
                            if baris["skenario"] == skenario and baris["varian"] == nama_varian]
            if daftar_waktu:
                print(f"{skenario} {nama_varian:22} {statistics.mean(daftar_waktu):.3f}")

if __name__ == "__main__":
    main()