"""Verdikte an von Hand gesetzten Werten (DEMO-PLAYBOOK §12): jede Zahl im Text und jede Schwelle der Art steht hier."""

import stg_algorithm as A
import stg_constants as C
import stg_evaluation as ev
import stg_graph as G


def _cg(value=5.0, pool=5, iterations=7, columns=19, arcs=6899, integral=True, seconds=0.29):
    return G.CGResult(value, iterations, columns, arcs, 2564, seconds, seconds * 0.8, integral, pool, ())


def _flow(value=5.0, status="optimal"):
    return G.FlowResult(value if status == "optimal" else None, status, 0.1, 0.11, 6899, 2564, 9000, None)


def _a(cg=None, compact=5.0, opt=5, flow=None, size=(6075, 2652), lower=4, nodes=11, ms=0.2, capped=False):
    search = A.SearchResult(None if capped else opt, nodes, capped, 2)
    graph = None if cg is None else (cg.nodes, cg.arcs)
    return ev.Analysis(((1,),), 5, 9, lower, size, search, ms, graph, None if cg is None else compact, cg, flow if cg is None else (flow or _flow(opt)), None, None)


def test_bay_verdict_proven_at_the_root_names_lp_values_columns_and_iterations():
    kind, text = ev.verdict_bay(_a(_cg()))
    assert kind == "success" and text == ("Der Wurzelknoten beweist das Optimum: Spalten-LP 5 (gleich dem kompakten LP 5), Lösung aus den erzeugten Spalten 5, Optimum 5; "
                                          "19 Spalten von 6 899 Kanten in 7 Iterationen.")
    kind, text = ev.verdict_bay(_a(_cg(value=6.0, pool=6, iterations=1, columns=14, arcs=16287), compact=5.0, opt=6))
    assert kind == "success" and "Spalten-LP 6 (strikt stärker als kompakten LP 5)" in text and "in 1 Iteration." in text
    assert "Spalten-LP 6,33" in ev.verdict_bay(_a(_cg(value=6.3333333, pool=7), compact=6.0, opt=7))[1]


def test_bay_verdict_when_the_root_does_not_prove_the_optimum():
    kind, text = ev.verdict_bay(_a(_cg(value=7.0, pool=8, iterations=30, columns=88, arcs=7025, integral=False), compact=7.0, opt=8))
    assert kind == "warning" and text.startswith("Der Wurzelknoten beweist das Optimum nicht (Branch and Price müsste verzweigen): Spalten-LP 7 (gleich dem kompakten LP 7)")
    assert "Lösung aus den erzeugten Spalten 8, Optimum 8" in text
    kind, text = ev.verdict_bay(_a(_cg(value=4.0, pool=5, integral=False), compact=4.0, opt=4))
    assert kind == "warning"                                                                         # LP gleich Optimum, aber der Spaltenvorrat enthält die Lösung nicht
    assert ev.verdict_bay(_a(_cg(value=4.0 + 1e-9, pool=4), compact=4.0, opt=4))[0] == "success"       # Rundungsrauschen eines Lösers zählt nicht als Lücke


def test_bay_verdict_when_the_graphs_are_too_big():
    kind, text = ev.verdict_bay(_a(None, size=(21360, 6622), opt=10, lower=7, nodes=100, ms=1.1))
    assert kind == "info" and text == ("Die Stapelgraphen hätten mehr als 60 000 Kanten (das kompakte Modell hat 21 360 Variablen): Die Spaltenformulierung wird hier nicht gerechnet. "
                                       "Die Suche löst die Bucht mit 100 Knoten in 1,1 ms (Optimum 10, Untergrenze 7).")


def test_result_rows_by_hand():
    rows = ev.result_rows(_a(_cg()))
    names = [r["name"] for r in rows]
    assert names == ["Suche (IDA* mit Untergrenze und Merken)", "Kompaktes LP (Stück 7)", "Untergrenze (Stück 2)", "Spalten-LP (Wurzelknoten)", "Lösung aus den erzeugten Spalten (Preis und Verzweige)",
                     "Ganzzahliger Pfadfluss (alle Spalten)"]
    assert rows[0] == {"name": names[0], "value": "5", "effort": "11 Knoten, 0,2 ms"} and rows[1]["effort"] == "6 075 Variablen, 2 652 Zeilen"
    assert rows[3] == {"name": names[3], "value": "5", "effort": "7 Iterationen, 19 Spalten von 6 899 Kanten, 0,29 s"} and rows[5]["value"] == "5" and rows[5]["effort"] == "2 564 Knoten, 6 899 Kanten, 0,11 s"
    big = ev.result_rows(_a(None, size=(21360, 6622), opt=10))
    assert [r["name"] for r in big] == ["Suche (IDA* mit Untergrenze und Merken)", "Untergrenze (Stück 2)", "Spaltenformulierung"] and big[2]["value"] == "nicht gerechnet"
    assert ev.result_rows(_a(_cg(), flow=_flow(status="time_limit")))[5]["value"] == "kein Beweis"


def _stats(arcs_med=5464, arcs_max=20671, vars_=6075, containers=9, **extra):
    base = {"n": 40, "containers": containers, "compact_vars": vars_, "arcs": {"median": arcs_med, "max": arcs_max}, "cols_equal": 37, "compact_equal": 31, "stronger": 8, "weaker": 0,
            "gap_cols": {"median": 0.0, "max": 1.0}, "gap_compact": {"median": 0.0, "max": 2.0}}
    base.update(extra)
    return base


def test_size_verdict_two_states_and_numbers():
    kind, text = ev.verdict_size(_stats(), "3 × 3")
    assert kind == "info" and text == ("3 × 3 (9 Container): Die Stapelgraphen haben im Median 5 464 Kanten (Maximum 20 671), das kompakte Modell 6 075 Variablen (Verhältnis 0,90). "
                                       "Der Stapelgraph ist hier kleiner als das kompakte Modell.")
    assert ev.verdict_size(_stats(arcs_med=6075), "x")[0] == "info"                                  # genau gleich groß zählt noch als „kleiner oder gleich“
    kind, text = ev.verdict_size(_stats(arcs_med=91338, vars_=21360, containers=12), "4 × 3")
    assert kind == "warning" and "Verhältnis 4,28" in text and text.endswith("größer als das kompakte Modell.")
    assert C.SMALL_GRAPH_RATIO == 1.0


def test_strength_verdict_three_states_and_numbers():
    kind, text = ev.verdict_strength(_stats(stronger=8), "3 × 3")
    assert kind == "info" and text == ("3 × 3: Das Spalten-LP trifft das Optimum in 37 von 40 Buchten, das kompakte in 31; strikt stärker in 8, schwächer in 0; "
                                       "Optimum minus LP-Wert im Median 0 (Maximum 1) gegen 0 (Maximum 2). Die Spaltenformulierung ist hier in einem Teil der Buchten stärker.")
    assert ev.verdict_strength(_stats(stronger=20), "x")[0] == "success" and ev.verdict_strength(_stats(stronger=19), "x")[0] == "info"          # genau die Hälfte zählt als „meist“
    kind, text = ev.verdict_strength(_stats(stronger=0), "x")
    assert kind == "info" and text.endswith("Beide Schranken sind hier gleich gut.")
    kind, text = ev.verdict_strength(_stats(weaker=1), "x")
    assert kind == "warning" and "schwächer" in text and C.STRONG_SHARE == 0.5


def _cgstats(proven=39, n=40, integral=36, unproven=None, share=0.0051, price=0.8):
    return _stats(cg={"n": n, "iterations": {"median": 7.0, "max": 38}, "columns": {"median": 19.0, "max": 107}, "share": share, "seconds": {"median": 0.7, "max": 5.6}, "price_share": price,
                      "integral": integral, "pool_equal": 40, "proven": proven, "proven_compact": 31, "unproven": unproven or []})


def test_columns_verdict_two_states_and_numbers():
    kind, text = ev.verdict_columns(_cgstats(), "3 × 3")
    assert kind == "warning" and text == ("3 × 3: 19 Spalten im Median (Maximum 107) von 5 464 Kanten in 7 Iterationen; das Preisproblem braucht 80 % der Zeit; der Wurzelknoten beweist das Optimum "
                                          "in 39 von 40 Buchten (mit dem kompakten LP: 31), die Wurzel ist in 36 ganzzahlig. In 1 Buchten müsste Branch and Price verzweigen.")
    kind, text = ev.verdict_columns(_cgstats(proven=40), "3 × 2")
    assert kind == "info" and text.endswith("Verzweigen wäre hier nie nötig.")


def test_fix_verdict_two_states_and_numbers():
    kind, text = ev.verdict_fix({"n": 40, "solved": 40, "smaller": 9, "unplayable": 17, "wrong": 17}, "3 × 3")
    assert kind == "warning" and text == ("3 × 3: Ohne die Ordnungsbedingung (O) liefert der ganzzahlige Master in 9 von 40 Buchten ein zu kleines Optimum und in 17 eine Lösung, die sich nicht "
                                          "als Hubfolge nachspielen lässt; mit (O) stimmen alle.")
    kind, text = ev.verdict_fix({"n": 100, "solved": 100, "smaller": 0, "unplayable": 0, "wrong": 0}, "3 × 2")
    assert kind == "info" and text == "3 × 2: Hier macht die Ordnungsbedingung (O) keinen Unterschied: In allen 100 Buchten stimmt auch der Master ohne sie."


def test_path_rows_by_hand(mini):
    cp = G.build_coupled(*mini)
    flow = G.solve_flow(cp, True, 60)
    rows = ev.path_rows(cp, flow.paths)
    assert len(rows) == 18 and [r["period"] for r in rows if r["stack"] == 1] == [1, 2, 3, 4, 5, 6]                  # drei Stapel, sechs Perioden
    first = [r for r in rows if r["stack"] == 1 and r["period"] == 1][0]
    assert first["content"] == "(1, 4)" and first["departures"] == "4" and first["arrivals"] == "–"                    # die 4 geht in Periode 1 vom ersten Stapel ab
    assert sum(1 for r in rows if r["arrivals"] != "–") == 2 and sum(1 for r in rows if r["departures"] != "4") >= 1   # zwei Zugänge im Ganzen (zwei Umlagerungen)
