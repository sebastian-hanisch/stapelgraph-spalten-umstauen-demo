"""Gemeinsame Fixtures: die Mini-Buchten, an denen jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def mini():
    """Die Mini-Bucht (einzelner Blocker aus Stück 2): 3 Stapel mit je 2 Containern, Höchsthöhe 4, von unten nach oben (1, 4), (5, 2), (6, 3). Untergrenze 1, Optimum 2.

    Handrechnung des Stapelgraphen: Die 4 muss in Periode 1 weg (liegt über der 1). Die Stapelgraphen haben zusammen 133 Knoten und 264 Kanten (Aufzählung der Zustände
    (Periode, Inhalt) und der Zugangslisten je Zustand); das kompakte Modell aus Stück 7 hat 1 692 Variablen. Die Spaltengenerierung braucht 4 Iterationen und 7 Spalten."""
    return ((1, 4), (5, 2), (6, 3)), 4


@pytest.fixture
def counter():
    """Das Gegenbeispiel aus Stück 1: (3, 6), (2, 4), (1, 5), Höchsthöhe 4. Untergrenze 3, Optimum 4. Stapelgraphen: 152 Knoten, 304 Kanten; Spalten-LP 4 (gleich dem Optimum),
    die Wurzel ist gebrochen und die Lösung aus den erzeugten Spalten kostet 5: der Wurzelknoten beweist das Optimum nicht."""
    return ((3, 6), (2, 4), (1, 5)), 4


@pytest.fixture
def fix():
    """Drei Blocker über der 1: (1, 6, 7, 8), (2, 3), (4, 5), Höchsthöhe 4. Optimum 8; Stapelgraphen 1 216 Knoten, 3 226 Kanten; Spalten-LP 8."""
    return ((1, 6, 7, 8), (2, 3), (4, 5)), 4
