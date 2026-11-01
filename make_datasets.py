import csv
from pathlib import Path

BASE = Path(__file__).parent
SRC = BASE / "data"
N_TEORI_S2, N_LAB_S2 = 5, 1      
N_TEORI_S3, N_LAB_S3 = 4, 1      


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
    for r in ruang:                      
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