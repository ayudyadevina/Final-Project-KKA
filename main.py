import argparse
import csv
from dataclasses import replace
from pathlib import Path
from solver import VARIAN, muat_csp, simpan_jadwal, solve
from verify import verifikasi, load_jadwal_csv

PILIHAN_ALGO = {
    "bt": "BT",
    "mrv": "BT + MRV (+degree)",
    "mrv+lcv": "BT + MRV + LCV",
    "mrv+fc": "BT + MRV + FC",
    "mac": "BT + MAC (AC-3)",
}

def tampilkan_jadwal(jadwal, folder):
    with open(Path(folder) / "slot.csv", newline="", encoding="utf-8-sig") as f:
        daftar_slot = list(csv.DictReader(f))
    for baris in daftar_slot:
        kelas_di_slot = [(kls, rng) for kls, (slot_kelas, rng) in jadwal.items() if slot_kelas.id == baris["id_slot"]]
        if not kelas_di_slot:
            continue
        print(f"{baris['hari']} {baris['mulai']}-{baris['selesai']} ({baris['id_slot']})")
        for kls, rng in sorted(kelas_di_slot, key=lambda x: x[0].id):
            print(f"   {kls.id:10} {rng.id:8} sem {kls.semester}  {','.join(sorted(kls.dosen))}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/S1")
    parser.add_argument("--algo", default="bt", choices=list(PILIHAN_ALGO))
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", default="hasil/jadwal.csv")
    args = parser.parse_args()
    csp = muat_csp(args.data)
    konfig = replace(VARIAN[PILIHAN_ALGO[args.algo]], timeout=args.timeout, seed=args.seed)
    try:
        jadwal, stat = solve(csp, konfig)
    except NotImplementedError as err:
        print(err)
        return
    if jadwal is None:
        print(f"Tidak ada jadwal ({stat['status']})")
    else:
        tampilkan_jadwal(jadwal, args.data)
        simpan_jadwal(jadwal, args.out)
    print("\nMetrik")
    for nama, nilai in stat.items():
        print(f"  {nama:11}: {nilai:.3f}" if nama == "time" else f"  {nama:11}: {nilai}")
    if jadwal:
        pelanggaran = verifikasi(load_jadwal_csv(args.out), args.data)
        if pelanggaran:
            print(f"\nVerify GAGAL, {len(pelanggaran)} pelanggaran")
            for item in pelanggaran[:10]:
                print(" ", item)
        else:
            print("\nVerify LOLOS, semua constraint terpenuhi")

if __name__ == "__main__":
    main()