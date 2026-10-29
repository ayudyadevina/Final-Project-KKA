"""
verify.py - Pengecek jadwal INDEPENDEN (task 11).

Sengaja TIDAK mengimpor csp.py / solver.py. Semua aturan ditulis ulang
dari nol dan data dibaca sendiri dari CSV, supaya bug di csp.py atau
solver tetap tertangkap di sini.

Format jadwal (CSV): id_kelas,id_slot,id_ruang
  atau dict Python: {"TG-B": ("Sen-1", "IF-101"), ...}

Pemakaian:
  python verify.py hasil/jadwal.csv
  python verify.py hasil/jadwal.csv --data data
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent


def _read(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_jadwal_csv(path):
    return {r["id_kelas"]: (r["id_slot"], r["id_ruang"]) for r in _read(path)}


def verifikasi(jadwal, data_dir=BASE / "data"):
    """Kembalikan list string pelanggaran. List kosong = jadwal valid."""
    data_dir = Path(data_dir)
    kelas = {r["id_kelas"]: r for r in _read(data_dir / "kelas.csv")}
    ruang = {r["id_ruang"]: r for r in _read(data_dir / "ruang.csv")}
    slot = {r["id_slot"] for r in _read(data_dir / "slot.csv")}
    v = []

    # 0. kelengkapan: tiap kelas terjadwal tepat sekali, tidak ada kelas asing
    for kid in kelas:
        if kid not in jadwal:
            v.append(f"[LENGKAP] {kid} belum dijadwalkan")
    for kid in jadwal:
        if kid not in kelas:
            v.append(f"[LENGKAP] {kid} tidak ada di kelas.csv")

    # 1. nilai valid + U1 (tipe ruang cocok)
    for kid, (s, r) in jadwal.items():
        if kid not in kelas:
            continue
        if s not in slot:
            v.append(f"[NILAI] {kid}: slot '{s}' tidak dikenal")
        if r not in ruang:
            v.append(f"[NILAI] {kid}: ruang '{r}' tidak dikenal")
        elif ruang[r]["tipe"] != kelas[kid]["tipe"]:
            v.append(f"[U1] {kid} ({kelas[kid]['tipe']}) di ruang {r} ({ruang[r]['tipe']})")

    # kelompokkan kelas per slot, lalu cek antar pasangan di slot yang sama
    per_slot = defaultdict(list)
    for kid, (s, r) in jadwal.items():
        if kid in kelas:
            per_slot[s].append(kid)

    for s, ids in per_slot.items():
        ids = sorted(ids)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                ka, kb = kelas[a], kelas[b]
                if jadwal[a][1] == jadwal[b][1]:
                    v.append(f"[C1] {a} & {b}: ruang {jadwal[a][1]} sama di slot {s}")
                dosen_sama = set(ka["dosen"].split(";")) & set(kb["dosen"].split(";"))
                if dosen_sama:
                    v.append(f"[C2] {a} & {b}: dosen {sorted(dosen_sama)} sama di slot {s}")
                if ka["semester"] == kb["semester"] and ka["kelas"] == kb["kelas"]:
                    v.append(f"[C3] {a} & {b}: semester {ka['semester']} kelas {ka['kelas']} sama di slot {s}")
    return v


def main():
    p = argparse.ArgumentParser()
    p.add_argument("jadwal", nargs="?", default=str(BASE / "hasil" / "jadwal.csv"),
                   help="file CSV: id_kelas,id_slot,id_ruang (default: hasil/jadwal.csv)")
    p.add_argument("--data", default=str(BASE / "data"))
    args = p.parse_args()
    if not Path(args.jadwal).exists():
        print(f"File jadwal tidak ditemukan: {args.jadwal}")
        print("verify.py butuh file jadwal hasil solver (kolom: id_kelas,id_slot,id_ruang).")
        print("Belum ada solver? Pakai contoh: python3 verify.py hasil/tes_valid.csv")
        sys.exit(2)
    hasil = verifikasi(load_jadwal_csv(args.jadwal), args.data)
    if hasil:
        print(f"GAGAL: {len(hasil)} pelanggaran")
        for h in hasil:
            print(" ", h)
        sys.exit(1)
    print("LOLOS: jadwal valid, semua constraint terpenuhi")


if __name__ == "__main__":
    main()