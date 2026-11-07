"""Aussagen der Demo und des READMEs gegen die vorberechneten Bänder und gegen eine frische Nachrechnung kleiner Zellen (DEMO-PLAYBOOK §5, §12).

Zeiten werden nicht verglichen (sie schwanken); alle anderen Felder der gespeicherten Zelle müssen bei der Nachrechnung gleich sein."""

import stg_constants as C
import stg_evaluation as ev


def K(s, l):
    return ev.cell_key(s, l)


def _bands():
    return ev.load_bands()


def test_the_stored_cells_cover_exactly_the_cells_of_the_constants():
    z = _bands()["zellen"]
    assert set(z) == {ev.cell_key(s, l) for s, l, _ in C.SIZE_CELLS} and {ev.cell_key(s, l): n for s, l, n in C.SIZE_CELLS} == {k: z[k]["n"] for k in z}
    assert {k for k in z if "cg" in z[k]} == {ev.cell_key(s, l) for s, l, _ in C.CG_CELLS} and "flow" in z[ev.cell_key(3, 4)]
    k = _bands()["korrektur"]
    assert set(k) == {ev.cell_key(s, l) for s, l, _ in C.FIX_CELLS} and {kk: v["n"] for kk, v in k.items()} == {ev.cell_key(s, l): n for s, l, n in C.FIX_CELLS}


def test_the_column_lp_is_never_weaker_than_the_compact_lp_in_any_stored_bay():
    z = _bands()["zellen"]
    assert all(c["weaker"] == 0 for c in z.values())
    assert all(c["compact_equal"] <= c["cols_equal"] <= c["n"] and c["stronger"] <= c["n"] - c["compact_equal"] for c in z.values())
    assert sum(c["stronger"] for c in z.values()) == 14 and sum(c["n"] for c in z.values()) == 226


def test_where_the_column_lp_is_stronger_the_compact_lp_misses_the_optimum():
    for c in _bands()["zellen"].values():
        assert c["stronger"] <= c["n"] - c["compact_equal"]                                           # strikt stärker nur, wo das kompakte LP das Optimum verfehlt


def test_the_root_proves_the_optimum_in_all_but_three_of_220_bays():
    cg = {k: v["cg"] for k, v in _bands()["zellen"].items() if "cg" in v}
    assert sum(c["n"] for c in cg.values()) == 220 and sum(c["proven"] for c in cg.values()) == 217
    assert {k: [u["seed"] for u in c["unproven"]] for k, c in cg.items() if c["unproven"]} == {K(3, 2): [6, 10], K(3, 3): [7]}
    for c in cg.values():
        assert len(c["unproven"]) == c["n"] - c["proven"] and c["proven"] >= c["proven_compact"] and c["pool_equal"] >= c["proven"]
    seed7 = _bands()["zellen"][K(3, 3)]["cg"]["unproven"][0]
    assert (seed7["opt"], seed7["pool"], round(seed7["value"])) == (8, 8, 7)                          # echte Lücke: LP 7, Optimum 8


def test_the_small_cell_counts_are_the_ones_the_readme_quotes():
    z = _bands()["zellen"]
    assert (z[K(3, 3)]["arcs"]["median"], z[K(3, 3)]["arcs"]["max"], z[K(3, 3)]["compact_vars"], z[K(3, 3)]["containers"]) == (5464.0, 20671, 6075, 9)
    assert (z[K(3, 3)]["cols_equal"], z[K(3, 3)]["compact_equal"], z[K(3, 3)]["stronger"]) == (37, 31, 8) and z[K(3, 3)]["cg"]["proven"] == 39 and z[K(3, 3)]["cg"]["proven_compact"] == 31
    assert z[K(4, 3)]["arcs"]["max"] == 394444 and z[K(4, 3)]["cg"]["proven"] == 8 and z[K(4, 3)]["cg"]["proven_compact"] == 5 and z[K(3, 4)]["arcs"]["max"] == 549150
    assert all(z[k]["cg"]["share"] < 0.03 for k in z if "cg" in z[k])                                  # erzeugte Spalten sind höchstens 3 % der Kanten


def test_the_graph_is_smaller_than_the_compact_model_only_in_the_small_cells():
    z = _bands()["zellen"]
    smaller = sorted(k for k, c in z.items() if c["arcs"]["median"] <= c["compact_vars"])
    assert smaller == [K(3, 2), K(3, 3), K(4, 2)] and sorted(set(z) - set(smaller)) == [K(3, 4), K(4, 3), K(5, 2)]
    assert z[K(4, 3)]["arcs"]["median"] > 4 * z[K(4, 3)]["compact_vars"]


def test_the_correction_bands_say_the_order_constraint_is_needed():
    k = _bands()["korrektur"]
    assert k[K(3, 3)] == {"n": 40, "solved": 40, "smaller": 9, "unplayable": 17, "wrong": 17}
    assert k[K(3, 2)]["smaller"] == 0 and k[K(3, 2)]["unplayable"] == 4 and k[K(4, 2)]["unplayable"] == 4 and all(c["solved"] == c["n"] for c in k.values())


def test_a_fresh_recomputation_of_the_3_by_2_cell_reproduces_the_stored_band():
    stored = _bands()["zellen"][K(3, 2)]
    fresh = ev.cell_stats(ev.cell_rows(3, 2, C.DEFAULT_EXTRA, range(100), True), 3, 2)
    for key in ("n", "containers", "compact_vars", "cols_equal", "compact_equal", "stronger", "weaker", "arcs"):
        assert fresh[key] == stored[key], key
    assert fresh["cg"]["unproven"] == stored["cg"]["unproven"] and fresh["cg"]["proven"] == stored["cg"]["proven"] and fresh["cg"]["integral"] == stored["cg"]["integral"]
    assert fresh["cg"]["iterations"]["median"] == stored["cg"]["iterations"]["median"] and fresh["cg"]["columns"]["max"] == stored["cg"]["columns"]["max"]


def test_a_fresh_recomputation_of_the_order_constraint_check_reproduces_the_stored_band():
    stored = _bands()["korrektur"][K(3, 2)]
    fresh = ev.fix_stats(ev.fix_rows(3, 2, C.DEFAULT_EXTRA, range(100)))
    assert fresh == stored
