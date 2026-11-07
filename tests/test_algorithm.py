"""Suche und Simulator gegen Handrechnung und Eigenschaften (DEMO-PLAYBOOK §1b und §12)."""

import pytest

import stg_algorithm as A
from stg_scenario import make_bay, max_height


def test_autopop_blockers_and_canon_by_hand(mini):
    bay, _ = mini
    assert A.autopop(bay) == (bay, [])                                 # die 1 liegt unter der 4
    assert A.autopop(((2, 1), (3,))) == (((), ()), [1, 2, 3])
    assert A.blocker_count(bay) == 1 and A.stack_blockers((1, 2, 3)) == 2 and A.stack_blockers((3, 2, 1)) == 0
    assert A.target_stack(bay) == (1, 0) and A.target_stack(((5, 3), (2, 1))) == (1, 1)
    assert A.canon(((5, 2), (), (1, 4))) == ((), (1, 4), (5, 2))


def test_child_targets_by_hand():
    stacks = ((7,), (5, 8), (9,), ())                                  # Blocker 3 kommt von Stapel 1 (Index 0), die übergebene Bucht ist die ohne ihn
    assert A.child_targets(stacks, 0, 6, 3) == [1, 2, 3]               # engste Passung: erst Stapel 2 (5 > 3), dann Stapel 3 (9), dann der leere
    assert A.child_targets(((7,), (2, 8), (1,), (4,)), 0, 6, 9) == [3, 1, 2]
    assert A.child_targets(((1, 2), (3, 4), (5,)), 0, 2, 9) == [2]     # Höchsthöhe 2: nur Stapel 3 hat Platz


def test_search_by_hand(mini, counter):
    r = A.search(*mini)
    assert (r.optimum, r.nodes, r.capped, r.stages) == (2, 6, False, 2)
    r = A.search(*counter)
    assert (r.optimum, r.nodes, r.stages) == (4, 15, 2)


def test_search_cap_counts_nodes_over_all_stages(counter):
    bay, h = counter
    assert not A.search(bay, h, cap=15).capped
    r = A.search(bay, h, cap=14)                                       # genau ein Knoten zu wenig
    assert r.capped and r.optimum is None and r.nodes == 14


def test_sorted_bay_has_one_node():
    r = A.search(((5, 3), (2, 1), (6, 4)), 4)
    assert (r.optimum, r.nodes, r.stages) == (0, 1, 1)


def test_search_agrees_with_the_documented_phase_zero_numbers():
    for sd, nodes in ((12, 11),):                                      # 3 x 3 Bucht 12: 11 Knoten (Stück 5 und 6)
        assert A.search(make_bay(3, 3, sd), 5).nodes == nodes
    assert A.search(make_bay(5, 4, 2), 6) == A.SearchResult(9, 31, False, 2)


def test_replay_accepts_the_optimal_sequences(mini, counter):
    assert A.replay(*mini, [(1, 4, 1), (2, 4, 0)]) == 2                # die 4 auf Stapel 2, dann auf Stapel 1 zurück: zwei Hübe
    assert A.replay(*mini, [(1, 4, 2), (3, 4, 0)]) == 2                # die 4 auf Stapel 3, nach dem Abruf von 1 und 2 über der 3 noch einmal weg
    assert A.replay(((1,), (2,)), 2, []) == 0                          # schon sortiert: keine Umlagerung


def test_replay_rejects_every_rule_violation(mini):
    bay, h = mini
    with pytest.raises(ValueError, match="nicht oben"):
        A.replay(bay, h, [(1, 6, 0)])                                  # die 6 liegt nicht oben
    with pytest.raises(ValueError, match="nicht oben"):
        A.replay(bay, h, [(1, 5, 2)])                                  # die 5 liegt unten im Stapel 2
    with pytest.raises(ValueError, match="nicht über dem Ziel"):
        A.replay(((1,), (2,)), 2, [(2, 2, 0)])                         # in Periode 2 ist die 2 selbst das Ziel
    with pytest.raises(ValueError, match="nicht auf Stapel"):
        A.replay(bay, h, [(1, 4, 0)])                                  # dasselbe Stapel
    with pytest.raises(ValueError, match="nicht auf Stapel"):
        A.replay(bay, h, [(1, 4, 7)])                                  # kein Stapel
    with pytest.raises(ValueError, match="nicht auf Stapel"):
        A.replay(bay, 2, [(1, 4, 1)])                                  # Stapel 2 ist voll (Höchsthöhe 2)
    with pytest.raises(ValueError, match="liegt nicht oben"):
        A.replay(bay, h, [])                                           # die 4 wurde nicht bewegt: die 1 liegt nicht oben
    with pytest.raises(ValueError, match="übrige"):
        A.replay(((1,), (2,)), 2, [(3, 2, 0)])                         # Periode 3 gibt es bei zwei Containern nicht
