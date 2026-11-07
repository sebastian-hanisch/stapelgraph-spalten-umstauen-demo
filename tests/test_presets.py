"""Presets: jede Sonderbucht hat die Eigenschaft, für die sie steht (DEMO-PLAYBOOK §12), und die Hilfetexte nennen nur gemessene Zahlen."""

import pytest

import stg_constants as C
import stg_evaluation as ev
import stg_presets as P


def _analyse(name):
    p = C.PRESETS[name]
    return ev.analyse(ev.Settings(p["stacks"], p["layers"], p["extra"], p["seed"]))


def test_every_preset_is_inside_the_slider_bounds_and_has_help():
    for name, p in C.PRESETS.items():
        for key, state_key in P.PRESET_KEYS.items():
            lo, hi = P.bounds(state_key)
            assert lo <= p[key] <= hi, (name, key)
        assert name in C.PRESET_HELP and C.PRESET_HELP[name]
    assert set(C.PRESET_HELP) == set(C.PRESETS)


def test_everyday_bay_is_proven_at_the_root_with_equal_bounds():
    a = _analyse("Alltag (3 Stapel, 3 Lagen)")
    assert (a.containers, a.lower, a.optimum, a.graph, a.compact_size) == (9, 4, 5, (2564, 6899), (6075, 2652))
    assert abs(a.compact_lp - 5.0) < 1e-6 and abs(a.cg.value - 5.0) < 1e-6 and (a.cg.iterations, a.cg.columns) == (7, 19) and a.cg.integral and a.proven and not a.stronger


def test_mini_bay_is_the_single_blocker_of_stueck_2_with_permuted_stacks():
    a = _analyse("Die Mini-Bucht")
    assert a.bay == ((5, 2), (1, 4), (6, 3)) and sorted(a.bay) == sorted(((1, 4), (5, 2), (6, 3)))
    assert (a.lower, a.optimum, a.graph, a.compact_size) == (1, 2, (133, 264), (1692, 1020)) and (a.cg.iterations, a.cg.columns) == (4, 6) and a.proven


def test_strong_bay_has_a_strictly_stronger_column_lp_that_meets_the_optimum():
    a = _analyse("Die Schranke ist stärker (3 Stapel, 3 Lagen)")
    assert (a.lower, a.optimum, a.graph) == (5, 6, (1419, 3659)) and abs(a.compact_lp - 5.0) < 1e-6 and abs(a.cg.value - 6.0) < 1e-6
    assert a.cg.integral and a.proven and a.stronger


def test_branch_bay_needs_branching():
    a = _analyse("Verzweigen nötig (3 Stapel, 3 Lagen)")
    assert (a.optimum, a.graph) == (8, (2630, 7025)) and abs(a.cg.value - 7.0) < 1e-6 and abs(a.compact_lp - 7.0) < 1e-6 and a.cg.pool_value == 8
    assert not a.cg.integral and a.proven is False and (a.cg.iterations, a.cg.columns) == (30, 88)


def test_too_big_bay_is_not_computed_live():
    a = _analyse("Zu groß für live (4 Stapel, 3 Lagen)")
    assert a.graph is None and a.cg is None and a.compact_size == (21360, 6622) and a.optimum == 10 and a.lower == 7
    assert C.LIVE_MAX_ARCS == 60_000 and "394 000" in C.PRESET_HELP["Zu groß für live (4 Stapel, 3 Lagen)"]


def test_the_default_settings_are_the_everyday_preset():
    assert {s: P.SETTING_SPECS[s].default for s in P.SETTING_SPECS} == {"stacks_slider": 3, "layers_slider": 3, "extra_slider": 2, "seed_input": C.EVERYDAY_SEED}
    p = C.PRESETS["Alltag (3 Stapel, 3 Lagen)"]
    assert (p["stacks"], p["layers"], p["extra"], p["seed"]) == (3, 3, 2, 12)


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_apply_preset_writes_every_setting(name, monkeypatch):
    state = {}
    monkeypatch.setattr(P.st, "session_state", state)
    P.apply_preset(name)
    assert {PK: state[sk] for PK, sk in P.PRESET_KEYS.items()} == {k: C.PRESETS[name][k] for k in P.PRESET_KEYS}
    assert P.aktives_preset() == name
