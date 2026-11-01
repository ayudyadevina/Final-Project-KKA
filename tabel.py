import csv
import math
import statistics
from pathlib import Path
from collections import defaultdict
from html import escape

BASE = Path(__file__).parent
FILE_HASIL = BASE / "hasil" / "hasil.csv"
FOLDER_OUTPUT = BASE / "hasil"
FOLDER_GRAFIK = FOLDER_OUTPUT / "grafik"

URUTAN_VARIAN = [
    "BT",
    "BT + MRV (+degree)",
    "BT + MRV + LCV",
    "BT + MRV + FC",
    "BT + MAC (AC-3)",
]

LABEL_VARIAN = {
    "BT": "BT",
    "BT + MRV (+degree)": "MRV",
    "BT + MRV + LCV": "MRV+LCV",
    "BT + MRV + FC": "MRV+FC",
    "BT + MAC (AC-3)": "MAC",
}

# Warna dibuat menyerupai referensi grafik.
WARNA_VARIAN = ["#999999", "#0877B9", "#55B3E6", "#E66A00", "#009F78"]
BATAS_TIMEOUT_DEFAULT = 20.0


def angka(nilai):
    try:
        if nilai is None or str(nilai).strip() == "":
            return None
        return float(nilai)
    except (TypeError, ValueError):
        return None


def tulis_csv(nama_file, kolom, data):
    path = FOLDER_OUTPUT / nama_file
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=kolom, lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)
    print("Dibuat:", path)


def rata_rata(data, kolom):
    nilai = [angka(row.get(kolom)) for row in data]
    nilai = [x for x in nilai if x is not None]
    return statistics.mean(nilai) if nilai else None


def simpangan_baku(data, kolom):
    nilai = [angka(row.get(kolom)) for row in data]
    nilai = [x for x in nilai if x is not None]
    return statistics.stdev(nilai) if len(nilai) >= 2 else 0.0


def hitung_jumlah_kelas(skenario):
    file_kelas = BASE / "data" / skenario / "kelas.csv"
    if not file_kelas.exists():
        return None
    with open(file_kelas, newline="", encoding="utf-8-sig") as f:
        return sum(1 for _ in csv.DictReader(f))


def ambil_batas_timeout(hasil):
    # Ambil timeout dari baris eksperimen jika ada; jika tidak, gunakan 20 detik.
    for row in hasil:
        for kolom in ("timeout_limit", "batas_timeout", "timeout"):
            nilai = angka(row.get(kolom))
            if nilai is not None and nilai > 0:
                # Kolom timeout pada sebagian CSV berisi status, bukan batas.
                if kolom != "timeout":
                    return nilai
    return BATAS_TIMEOUT_DEFAULT


def svg_header(judul, subjudul, width=1120, height=650):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#222}'
        '.title{font-size:21px;font-weight:600}.sub{font-size:12px;fill:#555}'
        '.axis{font-size:12px}.legend{font-size:13px}.small{font-size:10px}'
        '</style>',
        f'<text x="{width/2}" y="30" text-anchor="middle" class="title">{escape(judul)}</text>',
        f'<text x="{width/2}" y="51" text-anchor="middle" class="sub">{escape(subjudul)}</text>',
    ]


def simpan_svg(nama, bagian):
    FOLDER_GRAFIK.mkdir(parents=True, exist_ok=True)
    path = FOLDER_GRAFIK / nama
    bagian.append("</svg>")
    path.write_text("\n".join(bagian), encoding="utf-8")
    print("Grafik dibuat:", path)


def grafik_waktu_referensi(hasil, skenario_list, varian_list, batas_timeout):
    """Grouped bar chart: skenario di sumbu X, warna untuk tiap varian."""
    W, H = 1120, 610
    left, right, top, bottom = 85, 30, 75, 145
    pw, ph = W-left-right, H-top-bottom

    # Log scale: grafik menampilkan rentang 0.001 hingga batas timeout.
    y_min = 0.001
    y_max = max(batas_timeout, 1.0)
    log_min, log_max = math.log10(y_min), math.log10(y_max)

    svg = svg_header(
        "Waktu rata-rata per skenario dan varian (5 run, skala log)",
        f"Batas timeout ({batas_timeout:g} s); error bar menunjukkan simpangan baku run solved",
        W, H
    )

    # Grid logaritmik.
    ticks = []
    p = math.floor(log_min)
    while 10 ** p <= y_max:
        ticks.append(10 ** p)
        p += 1
    if batas_timeout not in ticks:
        ticks.append(batas_timeout)

    def y_pos(value):
        value = max(y_min, min(y_max, value))
        return top + ph - ((math.log10(value)-log_min)/(log_max-log_min))*ph

    for tick in ticks:
        yy = y_pos(tick)
        svg.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{W-right}" y2="{yy:.1f}" stroke="#d9d9d9" stroke-width="1"/>')
        label = f"{tick:g}" if tick >= 1 else f"{tick:.3g}"
        svg.append(f'<text x="{left-10}" y="{yy+4:.1f}" class="axis" text-anchor="end">{label}</text>')

    # Garis batas timeout.
    y_timeout = y_pos(batas_timeout)
    svg.append(f'<line x1="{left}" y1="{y_timeout:.1f}" x2="{W-right}" y2="{y_timeout:.1f}" stroke="red" stroke-width="1.2" stroke-dasharray="5 3"/>')
    svg.append(f'<text x="{left+20}" y="{y_timeout-5:.1f}" class="small" fill="red">batas timeout ({batas_timeout:g} s)</text>')

    svg.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+ph}" stroke="#333"/>')
    svg.append(f'<line x1="{left}" y1="{top+ph}" x2="{W-right}" y2="{top+ph}" stroke="#333"/>')

    n_skenario = max(1, len(skenario_list))
    group_w = pw / n_skenario
    n_varian = max(1, len(varian_list))
    bar_w = min(48, (group_w * 0.78) / n_varian)
    gap = bar_w * 0.08
    full_w = n_varian * bar_w + (n_varian-1)*gap

    for si, skenario in enumerate(skenario_list):
        center = left + (si + 0.5)*group_w
        start_x = center - full_w/2
        jumlah_kelas = hitung_jumlah_kelas(skenario)
        label_skenario = skenario
        if jumlah_kelas is not None:
            label_skenario += f" ({jumlah_kelas} kelas)"

        for vi, varian in enumerate(varian_list):
            data = [r for r in hasil if r["skenario"] == skenario and r["varian"] == varian]
            solved = [r for r in data if r.get("status", "").strip().lower() == "solved"]
            timeout_count = sum(r.get("status", "").strip().lower() == "timeout" for r in data)
            x = start_x + vi*(bar_w+gap)
            avg = rata_rata(solved, "waktu")
            sd = simpangan_baku(solved, "waktu")

            # Jika seluruh run timeout, bar ditaruh pada batas timeout.
            # Jika sebagian solved, bar menunjukkan rata-rata run solved dan timeout diberi anotasi.
            if avg is None and timeout_count:
                plot_value = batas_timeout
                bar_color = WARNA_VARIAN[vi % len(WARNA_VARIAN)]
                y = y_pos(plot_value)
                height = top+ph-y
                svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{height:.1f}" fill="{bar_color}"/>')
                label = f"{timeout_count}/{len(data)} timeout"
                svg.append(
                    f'<text x="{x+bar_w/2:.1f}" y="{max(68,y-8):.1f}" class="small" '
                    f'text-anchor="middle" transform="rotate(-90 {x+bar_w/2:.1f} {max(68,y-8):.1f})">{escape(label)}</text>'
                )
            elif avg is not None:
                plot_value = min(avg, batas_timeout)
                y = y_pos(plot_value)
                height = top+ph-y
                color = WARNA_VARIAN[vi % len(WARNA_VARIAN)]
                svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{height:.1f}" fill="{color}"/>')

                # Error bar simpangan baku; dipotong di area grafik.
                if sd > 0:
                    y1 = y_pos(min(avg+sd, batas_timeout))
                    y2 = y_pos(max(avg-sd, y_min))
                    cx = x+bar_w/2
                    svg.append(f'<line x1="{cx:.1f}" y1="{y1:.1f}" x2="{cx:.1f}" y2="{y2:.1f}" stroke="#222" stroke-width="1.2"/>')
                    svg.append(f'<line x1="{cx-5:.1f}" y1="{y1:.1f}" x2="{cx+5:.1f}" y2="{y1:.1f}" stroke="#222"/>')
                    svg.append(f'<line x1="{cx-5:.1f}" y1="{y2:.1f}" x2="{cx+5:.1f}" y2="{y2:.1f}" stroke="#222"/>')

                if timeout_count:
                    label = f"{timeout_count}/{len(data)} timeout"
                    svg.append(
                        f'<text x="{x+bar_w/2:.1f}" y="68" class="small" text-anchor="middle" '
                        f'transform="rotate(-90 {x+bar_w/2:.1f} 68)">{escape(label)}</text>'
                    )

        svg.append(f'<text x="{center:.1f}" y="{top+ph+20}" class="axis" text-anchor="middle">{escape(label_skenario)}</text>')

    # Legend
    legend_y = H-35
    item_w = 150
    total_legend_w = len(varian_list)*item_w
    legend_x = (W-total_legend_w)/2
    for i, varian in enumerate(varian_list):
        x = legend_x+i*item_w
        color = WARNA_VARIAN[i % len(WARNA_VARIAN)]
        svg.append(f'<rect x="{x:.1f}" y="{legend_y-12}" width="20" height="11" fill="{color}"/>')
        svg.append(f'<text x="{x+26:.1f}" y="{legend_y-2}" class="legend">{escape(LABEL_VARIAN.get(varian,varian))}</text>')

    svg.append(f'<text x="23" y="{top+ph/2}" class="axis" text-anchor="middle" transform="rotate(-90 23 {top+ph/2})">Waktu (detik, skala log)</text>')
    simpan_svg("grafik_1_waktu_log.svg", svg)


def grafik_nodes(hasil, skenario_list, varian_list):
    W, H = 1120, 600
    left, right, top, bottom = 85, 35, 75, 125
    pw, ph = W-left-right, H-top-bottom
    svg = svg_header("Jumlah nodes expanded per skenario dan varian", "Rata-rata dari run berstatus solved", W, H)

    vals = []
    for s in skenario_list:
        for v in varian_list:
            d = [r for r in hasil if r["skenario"] == s and r["varian"] == v and r["status"].lower() == "solved"]
            a = rata_rata(d, "nodes")
            if a is not None:
                vals.append(a)
    ymax = max(vals)*1.15 if vals and max(vals)>0 else 1

    for i in range(6):
        val = ymax*i/5
        yy = top+ph-(val/ymax)*ph
        svg.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{W-right}" y2="{yy:.1f}" stroke="#ddd"/>')
        svg.append(f'<text x="{left-10}" y="{yy+4:.1f}" class="axis" text-anchor="end">{val:.0f}</text>')

    n_s = max(1,len(skenario_list))
    group_w = pw/n_s
    n_v = max(1,len(varian_list))
    bar_w = min(45, group_w*.78/n_v)
    gap = bar_w*.08
    full = n_v*bar_w+(n_v-1)*gap

    for si,s in enumerate(skenario_list):
        center=left+(si+.5)*group_w
        start=center-full/2
        for vi,v in enumerate(varian_list):
            d=[r for r in hasil if r["skenario"]==s and r["varian"]==v and r["status"].lower()=="solved"]
            a=rata_rata(d,"nodes")
            if a is None: continue
            h=(a/ymax)*ph
            x=start+vi*(bar_w+gap)
            y=top+ph-h
            svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{WARNA_VARIAN[vi%len(WARNA_VARIAN)]}"/>')
        jumlah=hitung_jumlah_kelas(s)
        label=f"{s} ({jumlah} kelas)" if jumlah is not None else s
        svg.append(f'<text x="{center:.1f}" y="{top+ph+22}" class="axis" text-anchor="middle">{escape(label)}</text>')

    legend_y=H-35
    item_w=150
    start=(W-len(varian_list)*item_w)/2
    for i,v in enumerate(varian_list):
        x=start+i*item_w
        svg.append(f'<rect x="{x:.1f}" y="{legend_y-12}" width="20" height="11" fill="{WARNA_VARIAN[i%len(WARNA_VARIAN)]}"/>')
        svg.append(f'<text x="{x+26:.1f}" y="{legend_y-2}" class="legend">{escape(LABEL_VARIAN.get(v,v))}</text>')
    svg.append(f'<text x="23" y="{top+ph/2}" class="axis" text-anchor="middle" transform="rotate(-90 23 {top+ph/2})">Nodes expanded</text>')
    simpan_svg("grafik_2_nodes.svg",svg)


def grafik_kelas_vs_waktu(hasil, skenario_list, varian_list):
    W,H=1120,600
    left,right,top,bottom=90,45,75,115
    pw,ph=W-left-right,H-top-bottom
    svg=svg_header("Jumlah kelas vs waktu penyelesaian", "Rata-rata waktu run solved; skenario tanpa solusi tidak ditampilkan",W,H)

    data={}
    for v in varian_list:
        pts=[]
        for s in skenario_list:
            n=hitung_jumlah_kelas(s)
            d=[r for r in hasil if r["skenario"]==s and r["varian"]==v and r["status"].lower()=="solved"]
            t=rata_rata(d,"waktu")
            if n is not None and t is not None:
                pts.append((n,t,s))
        if pts: data[v]=sorted(pts)

    if not data:
        print("Grafik 3 dilewati: data solved/jumlah kelas tidak tersedia.")
        return

    xs=[p[0] for pts in data.values() for p in pts]
    ys=[p[1] for pts in data.values() for p in pts]
    xmin,xmax=min(xs),max(xs)
    if xmin==xmax: xmin-=1; xmax+=1
    ymin=0
    ymax=max(ys)*1.15 if max(ys)>0 else 1

    for i in range(6):
        f=i/5
        yy=top+ph-f*ph
        val=ymin+f*(ymax-ymin)
        svg.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{W-right}" y2="{yy:.1f}" stroke="#ddd"/>')
        svg.append(f'<text x="{left-10}" y="{yy+4:.1f}" class="axis" text-anchor="end">{val:.3g}</text>')
        xx=left+f*pw
        xv=xmin+f*(xmax-xmin)
        svg.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{top+ph}" stroke="#eee"/>')
        svg.append(f'<text x="{xx:.1f}" y="{top+ph+22}" class="axis" text-anchor="middle">{xv:.0f}</text>')

    for vi,(v,pts) in enumerate(data.items()):
        coords=[]
        for n,t,s in pts:
            x=left+(n-xmin)/(xmax-xmin)*pw
            y=top+ph-(t-ymin)/(ymax-ymin)*ph
            coords.append((x,y,s))
        if len(coords)>1:
            pstr=" ".join(f"{x:.1f},{y:.1f}" for x,y,_ in coords)
            svg.append(f'<polyline points="{pstr}" fill="none" stroke="{WARNA_VARIAN[vi%len(WARNA_VARIAN)]}" stroke-width="2"/>')
        for x,y,s in coords:
            svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{WARNA_VARIAN[vi%len(WARNA_VARIAN)]}"/>')
            svg.append(f'<text x="{x+7:.1f}" y="{y-8:.1f}" class="small">{escape(s)}</text>')

    for i,v in enumerate(data):
        x=left+(i%3)*300
        y=H-35+(i//3)*18
        color=WARNA_VARIAN[i%len(WARNA_VARIAN)]
        svg.append(f'<line x1="{x}" y1="{y-4}" x2="{x+25}" y2="{y-4}" stroke="{color}" stroke-width="3"/>')
        svg.append(f'<text x="{x+32}" y="{y}" class="legend">{escape(LABEL_VARIAN.get(v,v))}</text>')
    svg.append(f'<text x="{W/2}" y="{H-5}" class="axis" text-anchor="middle">Jumlah kelas</text>')
    svg.append(f'<text x="23" y="{top+ph/2}" class="axis" text-anchor="middle" transform="rotate(-90 23 {top+ph/2})">Waktu rata-rata (detik)</text>')
    simpan_svg("grafik_3_kelas_vs_waktu.svg",svg)


def main():
    if not FILE_HASIL.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {FILE_HASIL}. Jalankan experiments.py terlebih dahulu.")

    with open(FILE_HASIL,newline="",encoding="utf-8-sig") as f:
        hasil=list(csv.DictReader(f))
    if not hasil:
        raise ValueError("hasil.csv kosong.")

    FOLDER_OUTPUT.mkdir(parents=True,exist_ok=True)
    grup=defaultdict(list)
    per_skenario=defaultdict(list)
    for r in hasil:
        grup[(r["skenario"],r["varian"])].append(r)
        per_skenario[r["skenario"]].append(r)

    skenario_list=sorted(per_skenario)
    varian_list=[v for v in URUTAN_VARIAN if any(k[1]==v for k in grup)]
    varian_list += sorted({k[1] for k in grup}-set(varian_list))

    rekap=[]
    for s in skenario_list:
        for v in varian_list:
            data=grup.get((s,v),[])
            if not data: continue
            solved=[r for r in data if r["status"].lower()=="solved"]
            mem=[angka(r.get("memori_kb")) for r in data]
            mem=[x for x in mem if x is not None]
            def avg(k):
                a=[angka(r.get(k)) for r in solved]
                a=[x for x in a if x is not None]
                return round(statistics.mean(a),6) if a else ""
            rekap.append({
                "skenario":s,"varian":v,"total_run":len(data),"solved":len(solved),
                "failure":sum(r["status"].lower()=="failure" for r in data),
                "timeout":sum(r["status"].lower()=="timeout" for r in data),
                "valid":sum(str(r.get("valid","")).lower() in ("true","1","yes","valid") for r in solved),
                "rata_rata_waktu_solved_s":avg("waktu"),
                "rata_rata_nodes_solved":avg("nodes"),
                "rata_rata_backtracks_solved":avg("backtracks"),
                "rata_rata_checks_solved":avg("checks"),
                "rata_rata_memori_kb":round(statistics.mean(mem),2) if mem else "",
                "jumlah_data_memori":len(mem),
            })

    status=[]
    for s in skenario_list:
        d=per_skenario[s]
        solved=[r for r in d if r["status"].lower()=="solved"]
        status.append({
            "skenario":s,"total_run":len(d),"solved":len(solved),
            "failure":sum(r["status"].lower()=="failure" for r in d),
            "timeout":sum(r["status"].lower()=="timeout" for r in d),
            "jadwal_valid":sum(str(r.get("valid","")).lower() in ("true","1","yes","valid") for r in solved),
        })

    performa=[{k:r[k] for k in (
        "skenario","varian","solved","rata_rata_waktu_solved_s",
        "rata_rata_nodes_solved","rata_rata_backtracks_solved","rata_rata_checks_solved"
    )} for r in rekap]
    memori=[{
        "skenario":r["skenario"],"varian":r["varian"],
        "rata_rata_memori_kb":r["rata_rata_memori_kb"],
        "jumlah_data_memori":r["jumlah_data_memori"],
        "catatan":"" if r["jumlah_data_memori"] else "N/A: pengukuran memori tidak tersedia"
    } for r in rekap]

    tulis_csv("tabel_rekap.csv",list(rekap[0].keys()),rekap)
    tulis_csv("tabel_status_skenario.csv",list(status[0].keys()),status)
    tulis_csv("tabel_performa.csv",list(performa[0].keys()),performa)
    tulis_csv("tabel_memori.csv",list(memori[0].keys()),memori)

    batas=ambil_batas_timeout(hasil)
    grafik_waktu_referensi(hasil,skenario_list,varian_list,batas)
    grafik_nodes(hasil,skenario_list,varian_list)
    grafik_kelas_vs_waktu(hasil,skenario_list,varian_list)

    print(f"\nSelesai: {len(hasil)} run dibaca.")
    print("Tabel CSV dan 3 grafik SVG tersimpan di folder hasil/.")


if __name__=="__main__":
    main()
