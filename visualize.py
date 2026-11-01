from dataclasses import replace
from pathlib import Path
import pandas as pd
import streamlit as st
from main import PILIHAN_ALGO
from solver import VARIAN, muat_csp, simpan_jadwal, solve
from verify import verifikasi, load_jadwal_csv

BASE = Path(__file__).resolve().parent
FOLDER_DATA = BASE / "data"
FILE_JADWAL = BASE / "hasil" / "jadwal.csv"
FILE_HASIL = BASE / "hasil" / "hasil.csv"
WARNA_SEMESTER = {3: "blue", 5: "green", 7: "orange"}


def jalankan(nama_data, kode_algo, batas_waktu, seed):
    folder = FOLDER_DATA / nama_data
    csp = muat_csp(folder)
    konfig = replace(VARIAN[PILIHAN_ALGO[kode_algo]], timeout=batas_waktu, seed=seed)
    jadwal, stat = solve(csp, konfig)
    daftar_slot = pd.read_csv(folder / "slot.csv")
    n_ruang = len(pd.read_csv(folder / "ruang.csv"))
    pelanggaran = None
    baris = []
    if jadwal:
        FILE_JADWAL.parent.mkdir(parents=True, exist_ok=True)
        simpan_jadwal(jadwal, FILE_JADWAL)
        pelanggaran = verifikasi(load_jadwal_csv(FILE_JADWAL), folder)
        for kls, (slot, ruang) in jadwal.items():
            baris.append({"kelas": kls.id, "nama": kls.nama, "dosen": ";".join(sorted(kls.dosen)), "semester": kls.semester, "slot": slot.id, "ruang": ruang.id})
    return {"stat": stat, "pelanggaran": pelanggaran, "jadwal": pd.DataFrame(baris),
            "slot": daftar_slot, "n_kelas": len(csp.variables), "n_ruang": n_ruang,
            "nama_data": nama_data, "algo": PILIHAN_ALGO[kode_algo]}

def badge(baris):
    warna = WARNA_SEMESTER.get(baris["semester"], "gray")
    return f":{warna}-background[{baris['kelas']} {baris['ruang']}]"

def tampilkan_hasil(h, cari):
    stat = h["stat"]
    st.subheader(f"{h['algo']} pada {h['nama_data']}")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Status", stat["status"])
    k2.metric("Waktu (detik)", f"{stat['time']:.3f}")
    k3.metric("Nodes", stat["nodes"])
    k4.metric("Backtracks", stat["backtracks"])
    k5.metric("Constraint checks", stat["checks"])
    if h["pelanggaran"] is None:
        st.error(f"Tidak ada jadwal ({stat['status']})")
        return
    if h["pelanggaran"]:
        st.error(f"Verify GAGAL, {len(h['pelanggaran'])} pelanggaran")
        st.write(h["pelanggaran"][:10])
    else:
        st.success("Verify LOLOS, semua constraint terpenuhi")
    df = h["jadwal"].merge(h["slot"], left_on="slot", right_on="id_slot")
    if cari:
        kunci = (df["kelas"] + " " + df["nama"] + " " + df["dosen"]).str.lower()
        df = df[kunci.str.contains(cari.lower(), regex=False)]
    kiri, kanan = st.columns(2)
    hari = list(h["slot"]["hari"].drop_duplicates())
    kiri.write("Kelas per hari")
    kiri.bar_chart(df["hari"].value_counts().reindex(hari, fill_value=0))
    kanan.write("Kelas per semester")
    kanan.bar_chart(df["semester"].astype(str).value_counts().sort_index())
    st.write("Jadwal mingguan  " + " ".join(
        f":{w}-background[Semester {s}]" for s, w in WARNA_SEMESTER.items()))
    for nama_hari, tab in zip(hari, st.tabs(hari)):
        with tab:
            for _, s in h["slot"][h["slot"]["hari"] == nama_hari].iterrows():
                isi = df[df["id_slot"] == s["id_slot"]].sort_values(["semester", "kelas"])
                st.markdown(f"**{s['mulai']} - {s['selesai']}** ({len(isi)} kelas)")
                st.markdown(" ".join(badge(b) for _, b in isi.iterrows()) or "_kosong_")

def tampilkan_eksperimen():
    if not FILE_HASIL.exists():
        st.info("hasil/hasil.csv belum ada. Jalankan python experiments.py dulu.")
        return
    df = pd.read_csv(FILE_HASIL)
    # Pastikan kolom numerik terbaca sebagai angka.
    for kolom in ("waktu", "nodes", "backtracks", "checks"):
        if kolom in df.columns:
            df[kolom] = pd.to_numeric(df[kolom], errors="coerce")

    semua = df.groupby(["skenario", "varian"]).agg(
        run=("run", "count"),
        solved=("status", lambda x: (x == "solved").sum()),
        failure=("status", lambda x: (x == "failure").sum()),
        timeout=("status", lambda x: (x == "timeout").sum()),
    )
    solved_df = df[df["status"] == "solved"]
    if not solved_df.empty:
        metrik_solved = solved_df.groupby(["skenario", "varian"]).agg(
            waktu_rata2=("waktu", "mean"),
            nodes_rata2=("nodes", "mean"),
            checks_rata2=("checks", "mean"),
            backtracks_rata2=("backtracks", "mean"),
        )
        ringkas = semua.join(metrik_solved, how="left")
    else:
        ringkas = semua

    st.subheader("Ringkasan per skenario dan varian")
    st.caption("Rata-rata waktu, nodes, checks, dan backtracks dihitung hanya dari run solved.")
    st.dataframe(ringkas, use_container_width=True)

    if not solved_df.empty:
        st.subheader("Perbandingan waktu eksekusi")
        waktu = solved_df.pivot_table(
            index="varian", columns="skenario", values="waktu", aggfunc="mean"
        )
        st.bar_chart(waktu)

        st.subheader("Perbandingan nodes expanded")
        nodes = solved_df.pivot_table(
            index="varian", columns="skenario", values="nodes", aggfunc="mean"
        )
        st.bar_chart(nodes)

    st.subheader("Status seluruh eksperimen")
    status = df.groupby(["skenario", "status"]).size().unstack(fill_value=0)
    st.bar_chart(status)

    with st.expander("Data mentah (satu baris per run)"):
        st.dataframe(df, use_container_width=True)

st.set_page_config(page_title="Penjadwalan Kuliah CSP", layout="wide")
st.title("Penjadwalan Kuliah dengan CSP")

st.sidebar.header("Pengaturan")
daftar_data = sorted(p.parent.name for p in FOLDER_DATA.glob("S*/kelas.csv"))
if not daftar_data:
    st.error("Dataset S1–S3 belum tersedia. Letakkan kelas.csv, ruang.csv, dan slot.csv di folder data/, lalu jalankan: python make_datasets.py")
    st.stop()

nama_data = st.sidebar.selectbox("Dataset", daftar_data)
kode_algo = st.sidebar.selectbox("Algoritma", list(PILIHAN_ALGO))
batas_waktu = st.sidebar.number_input("Timeout (detik)", min_value=1, value=30)
seed = st.sidebar.number_input("Seed (0 = urutan asli)", min_value=0, value=0)

if st.sidebar.button("Jalankan"):
    with st.spinner("Mencari jadwal..."):
        st.session_state["hasil"] = jalankan(nama_data, kode_algo, batas_waktu, seed or None)

tab_demo, tab_eksperimen = st.tabs(["Demo", "Hasil eksperimen"])
with tab_demo:
    cari = st.text_input("Cari kelas, mata kuliah, atau dosen")
    hasil = st.session_state.get("hasil")
    if hasil is None:
        st.info("Pilih dataset dan algoritma di sidebar, lalu klik Jalankan.")
    elif "error" in hasil:
        st.warning(hasil["error"])
    else:
        tampilkan_hasil(hasil, cari)
with tab_eksperimen:
    tampilkan_eksperimen()
