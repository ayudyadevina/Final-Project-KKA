"""
propagation.py - Forward checking (simpan nilai terhapus, restore saat mundur)
AC-3 / MAC = task 14 (A), belum ada.
"""


def forward_check(csp, var, val, assignment, domains):
    """
    Setelah var=val, buang nilai tetangga (belum terisi) yang konflik.
    Return list [(tetangga, [nilai terhapus])] untuk restore,
    atau None bila ada domain yang kosong (sudah dipulihkan di dalam fungsi ini).
    """
    removed = []
    for nb in csp.neighbors[var]:
        if nb in assignment:
            continue
        bad = [v for v in domains[nb] if csp.conflict(var, val, nb, v)]
        if not bad:
            continue
        bad_set = set(bad)
        domains[nb] = [v for v in domains[nb] if v not in bad_set]
        removed.append((nb, bad))
        if not domains[nb]:                  # wipeout -> batal
            restore(domains, removed)
            return None
    return removed


def restore(domains, removed):
    for nb, bad in removed:
        domains[nb].extend(bad)