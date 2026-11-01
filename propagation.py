from collections import deque

def forward_check(csp, var, val, assignment, domains):
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
        if not domains[nb]:                      
            restore(domains, removed)
            return None
    return removed

def restore(domains, removed):
    for nb, bad in removed:
        domains[nb].extend(bad)

def _revise(csp, z, nb, domains):
    """Nilai di domain z yang tidak punya dukungan di domain nb (busur z <- nb)."""
    dn = domains[nb]
    return [x for x in domains[z]
            if not any(not csp.conflict(z, x, nb, y) for y in dn)]

def _propagasi(csp, domains, ikatan, assigned, removed, awal):
    antrian, dalam = deque(), set()

    def picu(nb):
        d = domains[nb]
        satu_nilai = len(d) == 1
        satu_slot = len({s for s, _ in d}) == 1
        for z in csp.neighbors[nb]:
            if z in assigned or (z, nb) in dalam:
                continue
            if satu_slot if z in ikatan[nb] else satu_nilai:
                antrian.append((z, nb))
                dalam.add((z, nb))

    for nb in awal:
        picu(nb)
    while antrian:
        z, nb = antrian.popleft()
        dalam.discard((z, nb))
        bad = _revise(csp, z, nb, domains)
        if not bad:
            continue
        bad_set = set(bad)
        domains[z] = [v for v in domains[z] if v not in bad_set]
        removed.append((z, bad))
        if not domains[z]:                       
            restore(domains, removed)
            return None
        picu(z)
    return removed


def ac3_awal(csp, domains, ikatan):
    removed = _propagasi(csp, domains, ikatan, set(), [], list(csp.variables))
    return removed


def mac(csp, var, val, assignment, domains, ikatan):
    removed = forward_check(csp, var, val, assignment, domains)
    if removed is None:
        return None
    assigned = set(assignment)
    assigned.add(var)
    return _propagasi(csp, domains, ikatan, assigned, removed, [nb for nb, _ in removed])
