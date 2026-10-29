from heuristics import build_ikatan, select_var, order_values
from propagation import forward_check, restore


def _cek_didukung(config):
    if config.ac3:
        raise NotImplementedError("ac3/MAC belum diimplementasikan (task 14, PIC A).")


def solve(csp, config=None):
    config = config or Config()
    _cek_didukung(config)

    order = list(csp.variables)
    domains = {k: list(csp.domains[k]) for k in order}   # salinan kerja
    if config.seed is not None:
        rng = random.Random(config.seed)
        rng.shuffle(order)
        for d in domains.values():
            rng.shuffle(d)
    ikatan = build_ikatan(order)

    csp.constraint_checks = 0
    stats = {"nodes": 0, "backtracks": 0}
    assignment = {}
    t0 = time.perf_counter()
    deadline = t0 + config.timeout

    def consistent(var, val):
        return not any(csp.conflict(var, val, o, v) for o, v in assignment.items())

    def backtrack():
        if len(assignment) == len(order):
            return True
        var = select_var(order, assignment, domains, ikatan, config)
        for val in order_values(var, order, assignment, domains, ikatan, config):
            if time.perf_counter() >= deadline:
                raise _Timeout
            removed = None
            if config.fc:
                removed = forward_check(csp, var, val, assignment, domains)
                if removed is None:
                    continue
            elif not consistent(var, val):
                continue
            assignment[var] = val
            stats["nodes"] += 1
            if backtrack():
                return True
            del assignment[var]
            if removed is not None:
                restore(domains, removed)
        stats["backtracks"] += 1
        return False

    try:
        ok = backtrack()
        status = "solved" if ok else "failure"
    except _Timeout:
        ok, status = False, "timeout"

    stats["time"] = time.perf_counter() - t0
    stats["checks"] = csp.constraint_checks
    stats["status"] = status
    return (dict(assignment) if ok else None), stats