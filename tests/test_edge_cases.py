"""Randfälle, an denen Kernroutinen erfahrungsgemäß brechen (DEMO-PLAYBOOK §12)."""

import stg_algorithm as A
import stg_constants as C
import stg_evaluation as ev
import stg_graph as G


def test_one_container_and_an_empty_stack():
    bay = ((1,), ())
    cp = G.build_coupled(bay, 2)
    r = G.solve_flow(cp, True, 30)
    assert round(r.value) == 0 and G.paths_to_moves(cp, r.paths) == [] and A.replay(bay, 2, []) == 0
    cg = G.column_generation(bay, cp)
    assert abs(cg.value) < 1e-6 and cg.pool_value == 0 and G.proven_at_root(cg)


def test_two_stacks_one_hub():
    bay = ((1, 2), ())
    cp = G.build_coupled(bay, 3)
    r = G.solve_flow(cp, True, 30)
    assert round(r.value) == 1 and G.paths_to_moves(cp, r.paths) == [(1, 2, 1)] and A.replay(bay, 3, G.paths_to_moves(cp, r.paths)) == 1
    assert A.search(bay, 3).optimum == 1


def test_a_partially_filled_bay_with_unequal_heights():
    bay = ((1, 5, 4), (2,), (3, 6), ())
    cp = G.build_coupled(bay, 4)
    r = G.solve_flow(cp, True, 60)
    assert A.replay(bay, 4, G.paths_to_moves(cp, r.paths)) == round(r.value) == A.search(bay, 4).optimum


def test_only_one_free_slot_per_stack():
    bay = ((1, 5), (2, 3), (4, 6))                                        # Höchsthöhe 3: jeder Blocker findet höchstens einen freien Platz
    cp = G.build_coupled(bay, 3)
    r = G.solve_flow(cp, True, 60)
    assert round(r.value) == A.search(bay, 3).optimum


def test_no_room_means_infeasible():
    cp = G.build_coupled(((1, 3, 2), (4, 5, 6)), 3)                       # beide Stapel voll: die 2 und die 3 können nirgends hin
    r = G.solve_flow(cp, True, 30)
    assert r.status == "infeasible" and r.value is None and r.paths is None


def test_time_limit_never_claims_a_value_from_a_failed_solve():
    cp = G.build_coupled(((1, 6, 7, 8), (2, 3), (4, 5)), 4)
    r = G.solve_flow(cp, True, 0.001)
    assert r.status in ("time_limit", "optimal") and (r.status == "optimal") == (r.value is not None)


def test_analysis_without_the_graphs_when_they_are_too_big():
    a = ev.analyse(ev.Settings(4, 3, 2, C.TOOBIG_SEED))
    assert a.graph is None and a.cg is None and a.flow is None and a.compact_lp is None and a.stack_sizes is None and a.proven is None and a.stronger is None
    assert a.compact_size == (21360, 6622) and a.search.optimum == 10 and a.optimum == 10 and a.containers == 12


def test_analysis_with_the_graphs_checks_both_optima(mini):
    a = ev.analyse(ev.Settings(3, 2, 2, C.MINI_SEED))
    assert a.graph == (133, 264) and a.optimum == a.search.optimum == round(a.flow.value) == 2 and a.flow_hubs == 2 and a.proven is True and a.stronger is False
    assert abs(a.compact_lp - 2.0) < 1e-6 and a.cg.columns == 6 and len(a.stack_sizes) == 3 and sum(k for k, _ in a.stack_sizes) == 133
    assert ev.analyse(ev.Settings(3, 3, 2, 12), max_arcs=1000).graph is None                 # eigenes Limit der Live-Rechnung


def test_number_formats():
    assert ev.num(5) == "5" and ev.num(1234) == "1 234" and ev.num(394444) == "394 444"
    assert ev.num_f(5.0) == "5" and ev.num_f(71.5) == "71,5" and ev.num_f(1234.0) == "1 234" and ev.num_f(0.9999999999999987) == "1" and ev.num_f(5.499999999999999) == "5,5"
    assert ev.lp_text(5.0) == "5" and ev.lp_text(6.333333) == "6,33" and ev.lp_text(7.14285) == "7,14" and ev.lp_text(4.999999999) == "5" and ev.lp_text(12.5) == "12,50"
    assert ev.sec_text(0.03) == "0,03" and ev.sec_text(9.994) == "9,99" and ev.sec_text(10.04) == "10,0" and ev.ms_text(0.25) == "0,2" and ev.ms_text(12.4) == "12"
    assert ev.time_text(0.0009) == "0,9 ms" and ev.time_text(0.0042) == "4,2 ms" and ev.time_text(0.01) == "0,01 s" and ev.time_text(2.316) == "2,32 s" and ev.time_text(12.34) == "12,3 s"
    assert ev.percent_text(0.0259) == "2,6 %" and ev.percent_text(0.92) == "92 %" and ev.percent_text(0.098) == "9,8 %" and ev.percent_text(0.1) == "10 %"
    assert ev.iter_text(1) == "1 Iteration" and ev.iter_text(4) == "4 Iterationen" and ev.iter_text(29.5) == "29,5 Iterationen"


def test_cell_stats_without_column_generation_and_with_an_unproven_bay():
    rows = [{"seed": 0, "lb": 4, "opt": 6, "compact": 5.0, "value": 6.0, "arcs": 100, "nodes": 50, "build_s": 0.1, "iterations": None, "columns": None, "integral": None, "pool": None,
             "proven": None, "cg_s": None, "price_s": None, "flow_s": 1.0}]
    st = ev.cell_stats(rows, 3, 3)
    assert "cg" not in st and st["flow"]["seconds"]["median"] == 1.0 and st["stronger"] == 1 and st["weaker"] == 0 and st["cols_equal"] == 1 and st["compact_equal"] == 0
    rows = [{"seed": 7, "lb": 6, "opt": 8, "compact": 7.0, "value": 7.0, "arcs": 7025, "nodes": 3000, "build_s": 0.1, "iterations": 30, "columns": 88, "integral": False, "pool": 8, "proven": False,
             "cg_s": 1.0, "price_s": 0.8, "flow_s": None}]
    st = ev.cell_stats(rows, 3, 3)
    assert st["cg"]["unproven"] == [{"seed": 7, "opt": 8, "value": 7.0, "pool": 8}] and st["cg"]["proven"] == 0 and st["cg"]["pool_equal"] == 1 and st["cg"]["integral"] == 0
    assert st["gap_cols"] == {"median": 1.0, "max": 1.0} and st["gap_compact"] == {"median": 1.0, "max": 1.0} and round(st["cg"]["price_share"], 2) == 0.8
