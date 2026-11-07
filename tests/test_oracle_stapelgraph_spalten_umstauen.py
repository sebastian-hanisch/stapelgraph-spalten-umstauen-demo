"""Orakel-Test stapelgraph-spalten-umstauen-demo (ORACLE-PLAYBOOK, DEMO-PLAYBOOK §12): Optimum, Größe, Zertifikat und LP-Wert gegen ANDERE Rechenwege.

Orakel 1: Breitensuche über alle Buchtzustände (restricted) liefert das Optimum; der ganzzahlige Pfadfluss muss es treffen (3 x 2 vollständig, 4 x 2, 3 x 3).
Orakel 2: Jede Lösung des Pfadflusses wird zu einer Hubfolge zusammengesetzt und mit einem **eigenen Simulator** (nicht dem des Kerns) nach den Regeln nachgespielt.
Orakel 3: **Größe** des Stapelgraphen (Knoten, Kanten) und Zahl der Spalten (Pfade) gegen eine **zweite Aufzählung** über (Periode, Inhalt) mit Zählformeln, nicht über die Kantenliste.
Orakel 4: **Zertifikat**: die optimale Hubfolge der Breitensuche, in Kanten der Stapelgraphen übersetzt (eigene Übersetzung), erfüllt jede Nebenbedingung des Pfadflusses mit dem Zielwert
          des Optimums.
Orakel 5: Der LP-Wert des vollen Pfadflusses (HiGHS) gegen die Spaltengenerierung (kürzeste Pfade im Stapelgraphen): derselbe Wert.
Orakel 6: Der Master ohne die Ordnungsbedingung (O) ist zu schwach: er liefert ein zu kleines Optimum oder eine nicht spielbare Lösung.
Vorher an den Handzahlen geprüft: Mini-Bucht 133 Knoten und 264 Kanten, Optimum 2; Gegenbeispiel 152 und 304, Optimum 4."""

import math
from functools import lru_cache
from itertools import permutations

import numpy as np

import stg_algorithm as A
import stg_graph as G
from stg_scenario import canonical, make_bay, max_height


def _pop(st):
    st = [list(s) for s in st]
    while True:
        items = [c for s in st for c in s]
        if not items:
            return tuple(tuple(s) for s in st)
        t = min(items)
        hit = [s for s in st if s and s[-1] == t]
        if not hit:
            return tuple(tuple(s) for s in st)
        hit[0].pop()


def own_children(state, height):
    items = [c for s in state for c in s]
    t = min(items)
    src = next(i for i, s in enumerate(state) if t in s)
    c = state[src][-1]
    out = []
    for dst in range(len(state)):
        if dst == src or len(state[dst]) >= height:
            continue
        nxt = [list(s) for s in state]
        nxt[src].pop()
        nxt[dst].append(c)
        out.append((c, dst, tuple(tuple(s) for s in nxt)))
    return out


def bfs_sequence(bay, height):
    """Kürzeste Hubfolge [(Container, Zielstapel)] per Breitensuche mit Elternzeigern (eigener Rechenweg)."""
    start = _pop(bay)
    if not any(start):
        return []
    parent = {start: None}
    frontier = [start]
    while frontier:
        nxt = []
        for state in frontier:
            for c, dst, child in own_children(state, height):
                new = _pop(child)
                if new in parent:
                    continue
                parent[new] = (state, (c, dst))
                if not any(new):
                    seq, cur = [], new
                    while parent[cur] is not None:
                        cur, mv = parent[cur][0], parent[cur][1]
                        seq.append(mv)
                    return seq[::-1]
                nxt.append(new)
        frontier = nxt
    raise AssertionError("keine Lösung")


def own_replay(bay, height, moves):
    """Eigener Simulator: moves = [(Periode, Container, Zielstapel)] in Ausführungsreihenfolge. Gibt die Hubzahl zurück, wirft AssertionError bei Regelverstoß."""
    st = [list(s) for s in bay]
    n = sum(len(s) for s in st)
    todo = list(moves)
    hubs = 0
    for t in range(1, n + 1):
        src = next(i for i, s in enumerate(st) if t in s)
        pos_t = st[src].index(t)
        while todo and todo[0][0] == t:
            _, c, k = todo.pop(0)
            assert st[src][-1] == c and st[src].index(c) > pos_t, "nur der oberste Container über dem Ziel darf bewegt werden"
            assert k != src and len(st[k]) < height, "Zielstapel ungültig oder voll"
            st[k].append(st[src].pop())
            hubs += 1
        assert st[src][-1] == t, "das Ziel liegt nicht oben"
        st[src].pop()
    assert not todo and not any(st)
    return hubs


def children_count(t, cont, n_all, height):
    """Zahl der Kanten eines Knotens (t, Inhalt) nach den Zählformeln: eine Abgangskante, oder Summe der Anordnungen aller Zugangslisten."""
    if t in cont:
        return 1
    pool = [x for x in range(t + 1, n_all + 1) if x not in cont]
    return sum(math.perm(len(pool), k) for k in range(0, min(height - len(cont), len(pool)) + 1))


def count_graph(content, n_all, height):
    """(Knoten, Kanten, Pfade) eines Stapelgraphen per Zählung über (Periode, Inhalt): Zustände per Erreichbarkeit, Kanten und Pfade per Formel und Rekursion."""
    states = set()
    todo = [(1, tuple(content))]
    while todo:
        t, cont = todo.pop()
        if (t, cont) in states:
            continue
        states.add((t, cont))
        if t > n_all:
            continue
        if t in cont:
            todo.append((t + 1, cont[: cont.index(t)]))
        else:
            pool = [x for x in range(t + 1, n_all + 1) if x not in cont]
            for k in range(0, min(height - len(cont), len(pool)) + 1):
                for arr in permutations(pool, k):
                    todo.append((t + 1, cont + arr))
    arcs = sum(children_count(t, c, n_all, height) for t, c in states if t <= n_all)

    @lru_cache(maxsize=None)
    def paths(t, cont):
        if t > n_all:
            return 1
        if t in cont:
            return paths(t + 1, cont[: cont.index(t)])
        pool = [x for x in range(t + 1, n_all + 1) if x not in cont]
        return sum(paths(t + 1, cont + arr) for k in range(0, min(height - len(cont), len(pool)) + 1) for arr in permutations(pool, k))

    return len(states), arcs, paths(1, tuple(content))


def graph_paths(g):
    """Zahl der Quelle-Senke-Pfade im gebauten Graphen (Rekursion über die Kantenliste)."""
    out = {}
    for a in g.arcs:
        out.setdefault(a[0], []).append(a[1])

    @lru_cache(maxsize=None)
    def count(u):
        return 1 if u == g.sink else sum(count(v) for v in out.get(u, []))

    return count(g.source)


def certificate_vector(cp, bay, hubs):
    """Übersetzt eine Hubfolge [(Container, Zielstapel)] in einen Kantenvektor des Pfadflusses (eigene Übersetzung)."""
    n = cp.n
    offsets = np.cumsum([0] + [len(g.arcs) for g in cp.graphs])
    x = np.zeros(int(offsets[-1]))
    st = [list(s) for s in bay]
    todo = list(hubs)
    index = [{(g.content(u), t, arr, dep): a for a, (u, v, cost, t, arr, dep) in enumerate(g.arcs)} for g in cp.graphs]
    for t in range(1, n + 1):
        before = [tuple(s) for s in st]
        arr = {s: [] for s in range(len(st))}
        dep = {s: [] for s in range(len(st))}
        src = next(i for i, s in enumerate(st) if t in s)
        while st[src][-1] != t:
            c, k = todo.pop(0)
            assert st[src][-1] == c
            dep[src].append(c)
            arr[k].append(c)
            st[k].append(st[src].pop())
        st[src].pop()
        for s in range(len(st)):
            x[offsets[s] + index[s][(before[s], t, tuple(arr[s]), tuple(dep[s]))]] = 1.0
    assert not todo
    return x


def all_bays_3x2():
    seen = {}
    for perm in permutations(range(1, 7)):
        bay = tuple(tuple(perm[i * 2:(i + 1) * 2]) for i in range(3))
        seen.setdefault(canonical(bay), bay)
    return list(seen.values())


def test_oracle_on_the_hand_numbers(mini, counter, fix):
    assert len(bfs_sequence(*mini)) == 2 and len(bfs_sequence(*counter)) == 4 and len(bfs_sequence(*fix)) == 8
    for (bay, h), opt, size in ((mini, 2, (133, 264)), (counter, 4, (152, 304)), (fix, 8, (1216, 3226))):
        cp = G.build_coupled(bay, h)
        assert (cp.nodes, cp.arcs) == size and round(G.solve_flow(cp, True, 60).value) == opt


def test_path_flow_optimum_equals_the_breadth_first_search_and_the_solution_replays_with_an_own_simulator():
    checked = 0
    for stacks, layers, seeds in ((3, 2, 0), (4, 2, 60), (3, 3, 40)):
        h = max_height(layers, 2)
        bays = all_bays_3x2() if (stacks, layers) == (3, 2) else [make_bay(stacks, layers, sd) for sd in range(seeds)]
        for bay in bays:
            cp = G.build_coupled(bay, h)
            r = G.solve_flow(cp, True, 120)
            opt = len(bfs_sequence(bay, h))
            assert r.status == "optimal" and round(r.value) == opt, (stacks, layers, bay)
            moves = G.paths_to_moves(cp, r.paths)
            assert own_replay(bay, h, moves) == opt and A.replay(bay, h, moves) == opt
            checked += 1
    assert checked > 150


def test_graph_sizes_and_path_counts_equal_a_second_enumeration():
    for bay, h in ((((1, 4), (5, 2), (6, 3)), 4), (((3, 6), (2, 4), (1, 5)), 4), (make_bay(3, 3, 0), 5), (make_bay(3, 3, 1), 4), (make_bay(4, 2, 3), 4), (make_bay(3, 3, 5), 5)):
        cp = G.build_coupled(bay, h)
        n = cp.n
        for s, g in enumerate(cp.graphs):
            nodes, arcs, paths = count_graph(bay[s], n, h)
            assert (len(g.nodes), len(g.arcs)) == (nodes, arcs), (bay, s)
            assert graph_paths(g) == paths, (bay, s)
    # die größte bekannte Zahl der Spalten: 3 x 3 mit Höchsthöhe 5, Bucht 0
    paths = [count_graph(s, 9, 5)[2] for s in make_bay(3, 3, 0)]
    assert max(paths) > 100_000


def test_the_optimal_sequence_of_the_breadth_first_search_is_a_feasible_point_of_the_path_flow():
    for stacks, layers, seeds in ((3, 2, 40), (3, 3, 20)):
        h = max_height(layers, 2)
        for sd in range(seeds):
            bay = make_bay(stacks, layers, sd)
            cp = G.build_coupled(bay, h)
            hubs = bfs_sequence(bay, h)
            x = certificate_vector(cp, bay, hubs)
            c, a_eq, b_eq, a_ub, b_ub, _ = G.flow_matrices(cp)
            assert np.allclose(a_eq @ x, b_eq), (stacks, layers, sd)
            if a_ub is not None:
                assert np.all(a_ub @ x <= b_ub + 1e-9), (stacks, layers, sd)
            assert round(c @ x) == len(hubs)


def test_a_broken_point_violates_a_constraint():
    bay, h = ((1, 4), (5, 2), (6, 3)), 4
    cp = G.build_coupled(bay, h)
    x = certificate_vector(cp, bay, bfs_sequence(bay, h))
    _, a_eq, b_eq, a_ub, b_ub, _ = G.flow_matrices(cp)
    assert np.allclose(a_eq @ x, b_eq)
    broken = x.copy()
    broken[int(np.flatnonzero(x > 0.5)[0])] = 0.0                      # eine Kante des Pfades streichen: der Fluss reißt
    assert not np.allclose(a_eq @ broken, b_eq)


def test_column_generation_value_equals_the_lp_of_the_full_path_flow_on_many_bays():
    for stacks, layers, seeds in ((3, 2, 40), (4, 2, 20), (3, 3, 15)):
        h = max_height(layers, 2)
        for sd in range(seeds):
            bay = make_bay(stacks, layers, sd)
            cp = G.build_coupled(bay, h)
            assert abs(G.column_generation(bay, cp).value - G.solve_flow(cp, False, 60).value) < 1e-6, (stacks, layers, sd)


def test_the_master_without_the_order_constraint_is_too_weak():
    smaller = unplayable = 0
    for sd in range(40):
        bay = make_bay(3, 3, sd)
        cp = G.build_coupled(bay, 5, order=False)
        r = G.solve_flow(cp, True, 60)
        opt = len(bfs_sequence(bay, 5))
        if round(r.value) < opt:
            smaller += 1
        try:
            own_replay(bay, 5, G.paths_to_moves(cp, r.paths))
        except (AssertionError, ValueError):
            unplayable += 1
    assert (smaller, unplayable) == (9, 17)                             # 3 x 3, Buchten 0 bis 39
    for sd in range(30):                                                # mit (O) stimmen dieselben Buchten
        bay = make_bay(3, 3, sd)
        cp = G.build_coupled(bay, 5)
        r = G.solve_flow(cp, True, 60)
        assert round(r.value) == len(bfs_sequence(bay, 5)) and own_replay(bay, 5, G.paths_to_moves(cp, r.paths)) == round(r.value)
