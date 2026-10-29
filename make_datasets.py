"""
make_datasets.py - Generator 3 dataset skenario dari data/ utama (task 12).

Jalankan dari folder utama repo:  python3 make_datasets.py
Hasil: data/S1, data/S2, data/S3, masing-masing berisi kelas.csv, ruang.csv, slot.csv

  S1  sedang   : semester 3 saja (70 kelas), semua ruang
  S2  ketat    : semua kelas (114), hanya 5 ruang teori + 1 lab
                 (5 x 20 = 100 tempat untuk 96 kelas teori; masih ada solusi)
  S3  mustahil : semua kelas (114), 4 ruang teori + 1 lab
                 (4 x 20 = 80 tempat < 96 kelas teori; tidak mungkin ada solusi)

Semester di data asli: 3, 5, 7.
"""
import csv
from pathlib import Path

BASE = Path(__file__).parent
SRC = BASE / "data"
N_TEORI_S2, N_LAB_S2 = 5, 1      # S2: 5 ruang teori (100 tempat utk 96 kelas) + 1 lab
N_TEORI_S3, N_LAB_S3 = 4, 1      # S3: 4 x 20 = 80 < 96 kelas teori -> mustahil


def baca(nama):
    with open(SRC / nama, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def tulis(folder, nama, fields, rows):
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / nama, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def kurangi_ruang(ruang, n_teori, n_lab):
    out, cnt = [], {"teori": 0, "lab": 0}
    kuota = {"teori": n_teori, "lab": n_lab}
    for r in ruang:                      # ambil dari urutan di CSV (deterministik)
        if cnt[r["tipe"]] < kuota[r["tipe"]]:
            cnt[r["tipe"]] += 1
            out.append(r)
    return out


def main():
    fk, kelas = baca("kelas.csv")
    fr, ruang = baca("ruang.csv")
    fs, slot = baca("slot.csv")

    def sem(*s):
        return [k for k in kelas if k["semester"] in s]

    spec = {
        "S1": (sem("3"), ruang),
        "S2": (kelas, kurangi_ruang(ruang, N_TEORI_S2, N_LAB_S2)),
        "S3": (kelas, kurangi_ruang(ruang, N_TEORI_S3, N_LAB_S3)),
    }
    for nama, (k, r) in spec.items():
        folder = SRC / nama
        tulis(folder, "kelas.csv", fk, k)
        tulis(folder, "ruang.csv", fr, r)
        tulis(folder, "slot.csv", fs, slot)
        n_t = sum(1 for x in r if x["tipe"] == "teori")
        n_l = sum(1 for x in r if x["tipe"] == "lab")
        print(f"{nama}: {len(k):3d} kelas, {len(r):2d} ruang (teori {n_t}, lab {n_l}), {len(slot)} slot")


if __name__ == "__main__":
    main()