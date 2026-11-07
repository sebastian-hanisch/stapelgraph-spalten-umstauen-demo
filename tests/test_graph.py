"""Stapelgraph, Pfadfluss und Spaltengenerierung gegen Handrechnung und Eigenschaften (DEMO-PLAYBOOK §1b und §12)."""

import numpy as np
import pytest

import stg_algorithm as A
import stg_compact as M
import stg_graph as G
from stg_scenario import make_bay


def test_stack_graph_of_one_stack_by_hand():
    g = G.StackGraph((1, 4), 3, 3)                                       # ein Stapel (1, 4), drei Container insgesamt, Höchsthöhe 3
    # Periode 1: 1 liegt im Stapel, die 4 geht ab: Kante (1, (1, 4)) -> (2, ()), Abgang (4,)
    first = [a for a in g.arcs if a[3] == 1]
    assert len(first) == 1 and first[0][2] == 0 and first[0][4] == () and first[0][5] == (4,)
    assert g.content(first[0][0]) == (1, 4) and g.content(first[0][1]) == ()
    assert g.source == 0 and g.content(g.sink) == () and g.period(g.sink) == 4


def test_arrival_lists_are_ordered_and_limited_by_height():
    g = G.StackGraph((), 4, 2)                                           # leerer Stapel, Höchsthöhe 2, Container 1..4
    t1 = [a for a in g.arcs if a[3] == 1]
    lists = sorted(a[4] for a in t1)
    # Periode 1: Zugänge aus den Containern 2, 3, 4: leer, einzeln (3), geordnete Paare (6): 10 Kanten
    assert len(t1) == 10 and () in lists and (2,) in lists and (3, 2) in lists and (2, 3) in lists
    assert all(len(l) <= 2 for l in lists) and all(a[2] == len(a[4]) for a in t1)


def test_mini_graphs_by_hand(mini):
    cp = G.build_coupled(*mini)
    assert (cp.nodes, cp.arcs) == (133, 264) and cp.n == 6 and cp.use_order
    assert [a for _, a in cp.stack_sizes()] and sum(a for _, a in cp.stack_sizes()) == 264 and sum(k for k, _ in cp.stack_sizes()) == 133
    assert M.model_size(3, 4, 6)[0] == 1692                              # das kompakte Modell ist hier viel größer


def test_counterexample_and_three_blocker_graphs_by_hand(counter, fix):
    c = G.build_coupled(*counter)
    assert (c.nodes, c.arcs) == (152, 304)
    f = G.build_coupled(*fix)
    assert (f.nodes, f.arcs) == (1216, 3226)


def test_integral_path_flow_by_hand(mini, counter, fix):
    for (bay, h), opt in ((mini, 2), (counter, 4), (fix, 8)):
        cp = G.build_coupled(bay, h)
        flow = G.solve_flow(cp, True, 60)
        assert (flow.status, round(flow.value)) == ("optimal", opt) and A.search(bay, h).optimum == opt
        lp = G.solve_flow(cp, False, 60)
        assert lp.status == "optimal" and abs(lp.value - opt) < 1e-6 and lp.paths is None
        assert A.replay(bay, h, G.paths_to_moves(cp, flow.paths)) == opt


def test_column_generation_by_hand(mini, counter, fix):
    bay, h = mini
    cp = G.build_coupled(bay, h)
    cg = G.column_generation(bay, cp)
    assert abs(cg.value - 2.0) < 1e-6 and (cg.iterations, cg.columns, cg.arcs, cg.nodes) == (4, 7, 264, 133) and cg.integral and cg.pool_value == 2 and G.proven_at_root(cg)
    assert sum(w for _, w, _ in cg.solution) == pytest.approx(3.0)       # drei Stapel, je Gewicht 1
    bay, h = counter
    cg = G.column_generation(bay, G.build_coupled(bay, h))
    assert abs(cg.value - 4.0) < 1e-6 and cg.iterations == 9 and cg.columns == 25 and not cg.integral and cg.pool_value == 5 and not G.proven_at_root(cg)      # Wurzel gebrochen, Pool-Wert 5
    bay, h = fix
    cg = G.column_generation(bay, G.build_coupled(bay, h))
    assert abs(cg.value - 8.0) < 1e-6 and cg.iterations == 29 and cg.columns == 86 and cg.pool_value == 9 and not G.proven_at_root(cg)


def test_column_generation_value_equals_the_full_path_flow_lp():
    for stacks, layers, seeds in ((3, 2, 12), (4, 2, 8), (3, 3, 8)):
        h = layers + 2
        for sd in range(seeds):
            bay = make_bay(stacks, layers, sd)
            cp = G.build_coupled(bay, h)
            cg = G.column_generation(bay, cp)
            lp = G.solve_flow(cp, False, 60)
            assert abs(cg.value - lp.value) < 1e-6, (stacks, layers, sd)
            assert cg.columns <= cg.arcs and cg.value >= A.blocker_count(bay) - 1e-6                              # Untergrenze aus Stück 2 gilt auch für das Spalten-LP


def test_the_column_lp_is_never_weaker_than_the_compact_lp():
    for sd in range(10):
        bay = make_bay(3, 3, sd)
        cp = G.build_coupled(bay, 5)
        value = G.solve_flow(cp, False, 60).value
        compact, _ = M.lp_value(M.build(bay, 5))
        opt = A.search(bay, 5).optimum
        assert compact - 1e-6 <= value <= opt + 1e-6


def test_proven_at_root_uses_the_rounded_up_lp_value():
    cg = G.CGResult(6.0, 1, 1, 1, 1, 0.0, 0.0, True, 6, ())
    assert G.proven_at_root(cg)
    assert G.proven_at_root(G.CGResult(5.3, 1, 1, 1, 1, 0.0, 0.0, False, 6, ())) and G.proven_at_root(G.CGResult(5.0 + 1e-9, 1, 1, 1, 1, 0.0, 0.0, False, 5, ()))
    assert not G.proven_at_root(G.CGResult(7.0, 1, 1, 1, 1, 0.0, 0.0, True, 8, ())) and not G.proven_at_root(G.CGResult(4.0, 1, 1, 1, 1, 0.0, 0.0, False, None, ()))


def test_arc_limit_aborts_the_build_early(mini):
    with pytest.raises(G.ArcLimit):
        G.build_coupled(make_bay(4, 3, 0), 5, max_arcs=1000)
    assert G.build_coupled(*mini, max_arcs=264).arcs == 264              # genau die Kantenzahl reicht
    with pytest.raises(G.ArcLimit):
        G.build_coupled(*mini, max_arcs=263)                            # eine Kante zu wenig


def test_build_rejects_bad_input():
    with pytest.raises(ValueError):
        G.build_coupled(((1, 3), (4,)), 3)                              # Nummer 2 fehlt
    with pytest.raises(ValueError):
        G.build_coupled(((1, 2, 3), ()), 2)                             # Stapel höher als die Höchsthöhe


def test_sorted_bay_has_optimum_zero_and_integral_root():
    bay = ((5, 3), (2, 1), (6, 4))
    # sortierte Bucht: jede Spalte hat Kosten 0
    cp = G.build_coupled(bay, 4)
    cg = G.column_generation(bay, cp)
    assert abs(cg.value) < 1e-6 and cg.pool_value == 0 and cg.integral and G.proven_at_root(cg)
    assert round(G.solve_flow(cp, True, 60).value) == 0


def test_without_the_order_constraint_the_master_is_a_relaxation_that_can_cheat():
    bay = make_bay(3, 3, 4)                                              # Optimum 6; ohne (O) 5 (Phase 0: Bucht 4)
    cp = G.build_coupled(bay, 5, order=False)
    assert not cp.order and G.build_coupled(bay, 5).order
    r = G.solve_flow(cp, True, 60)
    assert round(r.value) == 5 < A.search(bay, 5).optimum == 6


def test_the_order_constraints_exist_only_where_two_containers_can_swap():
    cp = G.build_coupled(((1, 4), (5, 2), (6, 3)), 4)
    assert cp.order and all(viol and dep for viol, dep in cp.order.values())
    one = G.build_coupled(((1, 2), (3,)), 3)                             # höchstens ein Blocker: keine zwei Container, die vertauscht werden könnten
    assert one.order == {}


def test_paths_to_moves_rejects_a_departure_without_arrival(mini):
    bay, h = mini
    cp = G.build_coupled(bay, h)
    flow = G.solve_flow(cp, True, 60)
    broken = [list(p) for p in flow.paths]
    for s, path in enumerate(broken):                                   # den Pfad mit Zugängen durch eine Kante ohne Zugang ersetzen
        for t, a in enumerate(path):
            if cp.graphs[s].arcs[a][4]:
                alt = [b for b, arc in enumerate(cp.graphs[s].arcs) if arc[0] == cp.graphs[s].arcs[a][0] and not arc[4]]
                broken[s][t] = alt[0]
                with pytest.raises(ValueError):
                    G.paths_to_moves(cp, broken)
                return
    pytest.fail("kein Pfad mit Zugang gefunden")


def test_flow_matrices_shapes_and_the_coefficients(mini):
    cp = G.build_coupled(*mini)
    c, a_eq, b_eq, a_ub, b_ub, offsets = G.flow_matrices(cp)
    assert c.shape == (264,) and offsets[-1] == 264 and a_eq.shape[1] == 264 and a_eq.shape[0] == cp.nodes + len(cp.bal) and a_ub.shape[0] == len(cp.order) and len(b_ub) == a_ub.shape[0]
    assert set(np.unique(a_eq.data)) <= {-1.0, 1.0} and set(np.unique(a_ub.data)) == {1.0} and set(np.unique(b_ub)) == {1.0}
    assert int(c.sum()) == sum(a[2] for g in cp.graphs for a in g.arcs)


def test_heuristic_hubs_are_a_valid_start(counter, mini):
    for bay, h in (counter, mini):
        hubs = G.heuristic_hubs(bay, h)
        cp = G.build_coupled(bay, h)
        paths = G.paths_from_hubs(bay, cp, hubs)
        assert A.replay(bay, h, G.paths_to_moves(cp, paths)) == len(hubs) >= A.search(bay, h).optimum
        with pytest.raises(ValueError):
            G.paths_from_hubs(bay, cp, [(99, 0)] + hubs)               # bewegt nicht den obersten Container
