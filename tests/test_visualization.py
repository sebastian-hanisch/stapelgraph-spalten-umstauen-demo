"""Abbildungen an synthetischen Daten: Werte, Farben, gesperrte Achsen, Logarithmusachsen ohne add_hline (DEMO-PLAYBOOK §12)."""

import plotly.graph_objects as go

import stg_constants as C
import stg_visualization as V


def _locked(fig):
    return fig.layout.xaxis.fixedrange is True and fig.layout.yaxis.fixedrange is True


def test_blocker_cells_by_hand():
    assert V.blocker_cells(((1, 4), (5, 2), (6, 3))) == {(0, 1)}                                   # nur die 4 über der 1
    assert V.blocker_cells(((3, 6), (2, 4), (1, 5))) == {(0, 1), (1, 1), (2, 1)}
    assert V.blocker_cells(((1, 2, 3), (), (4,))) == {(0, 1), (0, 2)}                              # alles über der 1 blockiert, wenn es später abgerufen wird
    assert V.blocker_cells(((5, 3), (2, 1))) == set()


def test_bay_chart_colours_texts_and_the_height_line():
    fig = V.build_bay(((1, 4), (5, 2), (6, 3)), 4, target=1)
    assert _locked(fig) and len(fig.data) == 4 and list(fig.layout.yaxis.range) == [0, 4.35]
    assert list(fig.data[0].marker.color) == [C.COLOR_TARGET, C.COLOR_CELL, C.COLOR_CELL] and list(fig.data[0].text) == ["1", "5", "6"]
    assert list(fig.data[1].marker.color) == [C.COLOR_BLOCK, C.COLOR_CELL, C.COLOR_CELL] and list(fig.data[1].y) == [1, 1, 1]
    assert list(fig.data[2].y) == [0, 0, 0] and list(fig.data[2].text) == ["", "", ""]              # Lagen über der Füllung sind leer
    assert [s.y0 for s in fig.layout.shapes] == [4] and list(fig.layout.xaxis.ticktext) == ["Stapel 1", "Stapel 2", "Stapel 3"]
    assert V.build_bay(((1, 2),), 3).layout.height == 48 * 3 + 90


def test_stack_size_chart_uses_a_log_axis_and_no_hline():
    fig = V.build_stack_sizes([(21, 34), (91, 194), (21, 36)])
    assert _locked(fig) and fig.layout.yaxis.type == "log" and list(fig.data[0].y) == [34, 194, 36] and list(fig.data[0].x) == ["Stapel 1", "Stapel 2", "Stapel 3"]
    assert list(fig.data[0].text) == ["34", "194", "36"] and not fig.layout.shapes


def _cells():
    cg = {"columns": {"median": 19.0}}
    return {"3 × 2": {"containers": 6, "compact_vars": 1692, "arcs": {"median": 158.0, "max": 304}, "n": 100, "compact_equal": 100, "cols_equal": 100, "stronger": 0, "cg": {"columns": {"median": 5.0}}},
            "3 × 3": {"containers": 9, "compact_vars": 6075, "arcs": {"median": 5464.0, "max": 20671}, "n": 40, "compact_equal": 31, "cols_equal": 37, "stronger": 8, "cg": cg},
            "3 × 4": {"containers": 12, "compact_vars": 15660, "arcs": {"median": 307003.0, "max": 549150}, "n": 6, "compact_equal": 3, "cols_equal": 4, "stronger": 3}}


def test_size_chart_is_ordered_by_container_count_and_log_scaled():
    cells = _cells()
    fig = V.build_size({k: cells[k] for k in ("3 × 4", "3 × 2", "3 × 3")})
    assert _locked(fig) and fig.layout.yaxis.type == "log" and not fig.layout.shapes
    assert list(fig.data[0].x) == ["3 × 2 (6)", "3 × 3 (9)", "3 × 4 (12)"] and list(fig.data[0].y) == [158.0, 5464.0, 307003.0] and list(fig.data[1].y) == [304, 20671, 549150]
    assert list(fig.data[2].y) == [1692, 6075, 15660]


def test_strength_chart_shows_shares_in_percent_on_a_fixed_range():
    fig = V.build_strength(_cells())
    assert _locked(fig) and list(fig.layout.yaxis.range) == [0, 105] and [t.name for t in fig.data][0] == "kompaktes LP trifft das Optimum"
    assert list(fig.data[0].y) == [100.0, 77.5, 50.0] and [round(v, 6) for v in fig.data[1].y] == [100.0, 92.5, 66.666667] and list(fig.data[2].y) == [0.0, 20.0, 50.0]


def test_columns_chart_leaves_out_cells_without_column_generation():
    fig = V.build_columns(_cells())
    assert _locked(fig) and fig.layout.yaxis.type == "log" and list(fig.data[0].x) == ["3 × 2 (6)", "3 × 3 (9)"] and list(fig.data[1].y) == [5.0, 19.0]


def test_all_figures_are_plotly_figures():
    assert all(isinstance(f, go.Figure) for f in (V.build_bay(((1,),), 2), V.build_size(_cells()), V.build_strength(_cells()), V.build_columns(_cells())))
