"""Konstanten: Regler-Grenzen, feste Annahmen, Farben und Presets."""

STACKS_MIN, STACKS_MAX, DEFAULT_STACKS = 3, 5, 3          # Zahl der Stapel
LAYERS_MIN, LAYERS_MAX, DEFAULT_LAYERS = 2, 4, 3          # Anfangsfüllung je Stapel (Lagen)
EXTRA_MIN, EXTRA_MAX, DEFAULT_EXTRA = 1, 4, 2             # Platz: Höchsthöhe = Lagen + Zuschlag (Standard 2 wie in Stück 1 bis 7)
SEED_MAX = 999999

LIVE_MAX_ARCS = 60_000                                    # die Spaltengenerierung wird live nur gerechnet, wenn die Stapelgraphen zusammen höchstens so viele Kanten haben
SEARCH_CAP = 1_000_000                                    # Knotenlimit der Suche
FLOW_LIMIT = 60.0                                         # Zeitlimit des ganzzahligen Pfadflusses live in Sekunden

# Zellen der vorberechneten Tabellen: (Stapel, Lagen, Zahl der festen Buchten). Dieselben Buchten wie in Stück 4 bis 7 (Seeds ab 0, Platz 2).
SIZE_CELLS = ((3, 2, 100), (4, 2, 60), (3, 3, 40), (5, 2, 12), (4, 3, 8), (3, 4, 6))            # Größe der Stapelgraphen und Stärke der Schranke (A, B)
CG_CELLS = ((3, 2, 100), (4, 2, 60), (3, 3, 40), (5, 2, 12), (4, 3, 8))                         # Spaltengenerierung (C); 3 x 4 nur mit dem vollen Pfadfluss
FIX_CELLS = ((3, 2, 100), (4, 2, 60), (3, 3, 40))                                              # Gegenprobe: der Master ohne die Ordnungsbedingung (O)

STRONG_SHARE = 0.5                                        # Verdikt „die Schranke ist stärker“: Anteil der Buchten mit strikt stärkerem LP ab hier „oft“
SMALL_GRAPH_RATIO = 1.0                                   # Verdikt „Stapelgraph kleiner als das kompakte Modell“: Kanten / Variablen bis hier

COLOR_CELL = "#7a8fa6"
COLOR_BLOCK = "#b5545a"        # blockierend (liegt über einem früher abzurufenden)
COLOR_TARGET = "#2F6B65"       # nächster Abruf
COLOR_GRAPH, COLOR_COMPACT, COLOR_COLUMNS, COLOR_OPT, COLOR_LB = "#2F6B65", "#d9822b", "#4c78a8", "#1c4742", "#7a8fa6"
COLOR_LINES = ("#7a8fa6", "#2F6B65", "#d9822b", "#4c78a8")

# Sonderbuchten (in der Vormessung gefunden, Eigenschaften in tests/test_presets.py festgehalten)
MINI_SEED = 223        # 3 x 2: (5, 2), (1, 4), (6, 3) = der einzelne Blocker aus Stück 2 bis auf Vertauschen der Stapel: Stapelgraphen mit 133 Knoten und 264 Kanten
EVERYDAY_SEED = 12     # 3 x 3, Platz 2: Wurzel ganzzahlig und bewiesen, beide LP-Schranken gleich dem Optimum 5
STRONG_SEED = 27       # 3 x 3, Platz 2: kompaktes LP 5, Spalten-LP 6 = Optimum, Wurzel ganzzahlig
BRANCH_SEED = 7        # 3 x 3, Platz 2: Spalten-LP 7, Optimum 8: Verzweigen wäre nötig
TOOBIG_SEED = 0        # 4 x 3, Platz 2: Stapelgraphen mit rund 394 000 Kanten, nicht gerechnet
MINI_BAY = ((1, 4), (5, 2), (6, 3))                       # die Mini-Bucht des Modells von Hand (Stück 2: einzelner Blocker), Höchsthöhe 4
MINI_HEIGHT = 4
COUNTER_BAY = ((3, 6), (2, 4), (1, 5))                    # das Gegenbeispiel aus Stück 1, Höchsthöhe 4 (Wurzel gebrochen, LP gleich Optimum 4, Spaltenvorrat liefert 5)
COUNTER_HEIGHT = 4

PRESETS = {
    "Alltag (3 Stapel, 3 Lagen)": {"stacks": 3, "layers": 3, "extra": DEFAULT_EXTRA, "seed": EVERYDAY_SEED},
    "Die Mini-Bucht": {"stacks": 3, "layers": 2, "extra": DEFAULT_EXTRA, "seed": MINI_SEED},
    "Die Schranke ist stärker (3 Stapel, 3 Lagen)": {"stacks": 3, "layers": 3, "extra": DEFAULT_EXTRA, "seed": STRONG_SEED},
    "Verzweigen nötig (3 Stapel, 3 Lagen)": {"stacks": 3, "layers": 3, "extra": DEFAULT_EXTRA, "seed": BRANCH_SEED},
    "Zu groß für live (4 Stapel, 3 Lagen)": {"stacks": 4, "layers": 3, "extra": DEFAULT_EXTRA, "seed": TOOBIG_SEED},
}
PRESET_HELP = {
    "Alltag (3 Stapel, 3 Lagen)": "9 Container: Stapelgraphen mit rund 7 000 Kanten, 7 Iterationen mit 19 Spalten, die Wurzel ist ganzzahlig und beweist das Optimum 5.",
    "Die Mini-Bucht": "6 Container, ein einziger Blocker: Stapelgraphen mit 133 Knoten und 264 Kanten (das kompakte Modell hat 1 692 Variablen), 4 Iterationen, Optimum 2.",
    "Die Schranke ist stärker (3 Stapel, 3 Lagen)": "9 Container: das kompakte LP liefert 5, die Spaltenformulierung 6 und trifft damit das Optimum schon in der Wurzel.",
    "Verzweigen nötig (3 Stapel, 3 Lagen)": "9 Container: Spalten-LP 7, Optimum 8: der Wurzelknoten kann das Optimum nicht beweisen, Branch and Price müsste verzweigen.",
    "Zu groß für live (4 Stapel, 3 Lagen)": "12 Container: die Stapelgraphen hätten rund 394 000 Kanten und werden nicht gerechnet; die Suche löst die Bucht in Millisekunden.",
}
