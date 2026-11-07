"""Inhalt der App an festen Fällen (DEMO-PLAYBOOK §12): was im Ergebnis, in den Tabellen und in den Verdikten steht."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import stg_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(preset=None):
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    if preset:
        at.sidebar.button(key=f"preset_{preset}").click().run()
        assert not at.exception, [str(e) for e in at.exception]
    return at


def _md(at):
    return "\n".join(e.value for kind in (at.markdown, at.caption, at.info, at.success, at.warning) for e in kind)


def _metrics(at):
    return {m.label: (m.value, m.delta) for m in at.metric}


def test_default_page_has_the_sections_and_the_everyday_result():
    at = _run()
    subs = [s.value for s in at.subheader]
    assert [s for s in subs if s.startswith("🔬")] == [
        "🔬 Experiment: Die Spaltenformulierung der Mini-Bucht von Hand", "🔬 Experiment: Wie groß wird der Stapelgraph?", "🔬 Experiment: Wie stark ist die Schranke?",
        "🔬 Experiment: Wie viele Spalten braucht die Generierung?", "🔬 Experiment: Wann müsste Branch and Price verzweigen?", "🔬 Experiment: Warum braucht der Master die Ordnungsbedingung?"]
    assert "🚧 Wo die Annahmen enden" in subs
    m = _metrics(at)
    assert m["Stapelgraphen (Kanten)"] == ("6 899", "2 564 Knoten") and m["Spalten-LP (Wurzel)"] == ("5", "kompaktes LP 5") and m["Optimum"][0] == "5"
    assert m["Erzeugte Spalten"] == ("19", "7 Iterationen, von 6 899 Kanten")
    assert any(s.value.startswith("Der Wurzelknoten beweist das Optimum: Spalten-LP 5") for s in at.success)


def test_default_page_tables_quote_the_stored_numbers():
    text = _md(_run())
    assert "| 3 × 3 (9), 40 |" in text and "5 464 / 20 671" in text                                  # Größentabelle
    assert "| 3 × 3 (40) | 37 / 31 | 8 / 0 |" in text and "39 / 31 von 40" in text and "8 / 5 von 8" in text      # Stärketabelle
    assert "| 3 × 2 | 6 | 4 | 4 | 5 |" in text and "| 3 × 2 | 10 | 4 | 4 | 5 |" in text and "| 3 × 3 | 7 | 8 | 7 | 8 |" in text       # unbewiesene Buchten
    assert "In 3 von 220 Buchten" in text
    assert "| 3 × 3 (40) | 9 | 17 | 17 |" in text                                                       # Gegenprobe ohne (O)


def test_hand_section_reports_the_mini_bay_and_the_counterexample():
    text = _md(_run())
    assert "133 Knoten" in text and "264 Kanten" in text and "4 Iterationen" in text and "4 Iterationen und 7 Spalten" in text
    assert "152 Knoten" in text and "304 Kanten" in text and "Spalten-LP 4 (gleich dem Optimum 4), aber die Lösung aus den erzeugten Spalten kostet 5" in text


def test_every_stored_cell_is_in_the_size_table_and_the_custom_cell_note_is_correct():
    at = _run()
    text = _md(at)
    for s, l, n in C.SIZE_CELLS:
        assert f"| {s} × {l} (" in text
    assert "**Zelle 3 × 3 (Ihre Einstellung)**:" in text


def test_branch_preset_shows_a_warning_that_branching_is_needed():
    at = _run("Verzweigen nötig (3 Stapel, 3 Lagen)")
    assert any(w.value.startswith("Der Wurzelknoten beweist das Optimum nicht (Branch and Price müsste verzweigen)") for w in at.warning)
    assert _metrics(at)["Spalten-LP (Wurzel)"] == ("7", "kompaktes LP 7") and _metrics(at)["Optimum"][0] == "8"


def test_strong_preset_shows_the_strictly_stronger_bound():
    at = _run("Die Schranke ist stärker (3 Stapel, 3 Lagen)")
    assert any("strikt stärker als kompakten LP 5" in s.value for s in at.success) and _metrics(at)["Spalten-LP (Wurzel)"] == ("6", "kompaktes LP 5")


def test_too_big_preset_shows_no_graph_numbers_and_an_info():
    at = _run("Zu groß für live (4 Stapel, 3 Lagen)")
    m = _metrics(at)
    assert m["Stapelgraphen (Kanten)"][0] == "nicht gerechnet" and m["Spalten-LP (Wurzel)"][0] == "–" and m["Optimum"][0] == "10"
    assert any(i.value.startswith("Die Stapelgraphen hätten mehr als 60 000 Kanten") for i in at.info)


@pytest.mark.parametrize("stacks,layers", [(5, 4), (4, 4)])
def test_a_cell_without_stored_bands_says_so_and_does_not_crash(stacks, layers):
    at = _run()
    at.sidebar.slider(key="stacks_slider").set_value(stacks).run()
    at.sidebar.slider(key="layers_slider").set_value(layers).run()
    assert not at.exception
    assert any("nicht vorberechnet" in i.value for i in at.info)
