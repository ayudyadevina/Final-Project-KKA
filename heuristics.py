"""
heuristics.py - Pemilihan variabel (MRV + degree) dan urutan nilai (LCV)
"""
from collections import Counter


def build_ikatan(variables):
    ikatan = {k: set() for k in variables}
    for i, a in enumerate(variables):
        for b in variables[i + 1:]:
            if (a.dosen & b.dosen) or (a.semester == b.semester and a.grup == b.grup):
                ikatan[a].add(b)
                ikatan[b].add(a)
    return ikatan


def select_var(order, assignment, domains, ikatan, config):
    belum = [v for v in order if v not in assignment]
    if not config.mrv:
        return belum[0]                          # baseline: urutan tetap
    if config.degree:
        # MRV; seri dipecah: yang punya lebih banyak tetangga terikat belum terisi didahulukan
        return min(belum, key=lambda v: (
            len(domains[v]),
            -sum(1 for n in ikatan[v] if n not in assignment)))
    return min(belum, key=lambda v: len(domains[v]))


def order_values(var, order, assignment, domains, ikatan, config):
    vals = list(domains[var])
    if not config.lcv:
        return vals
    info = []
    for nb in order:
        if nb in assignment or nb is var:
            continue
        dom = domains[nb]
        info.append((nb in ikatan[var], set(dom), Counter(s for s, _ in dom)))

    def cost(val):
        # jumlah nilai tetangga yang tertutup bila var = val
        s, _ = val
        c = 0
        for terikat, dset, cnt in info:
            ada = val in dset                    # C1: (slot, ruang) persis sama
            if ada:
                c += 1
            if terikat:                          # C2/C3: seluruh slot s tertutup
                c += cnt[s] - (1 if ada else 0)
        return c

    return sorted(vals, key=cost)                # seri tetap urutan awal