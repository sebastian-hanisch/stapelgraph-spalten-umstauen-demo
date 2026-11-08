# Die Spaltenformulierung: Stapelgraph und Spaltengenerierung – Streamlit-Demo

<!-- TODO nach dem Deploy: direkt hierher den Live-Link setzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-stapelgraph-spalten-umstauen-demo.streamlit.app/)** -->

Achtes Stück der Konzepte-Reihe **„Umstauen: Untergrenze und Suche“** für die Website „Sebastian Hanisch – Operations Research und Machine Learning“. [Stück 7](https://sebastianhanisch-ilp-modell-umstauen-demo.streamlit.app/) hat das **kompakte, zeitindizierte Modell** gemessen. Dieses Stück stellt ihm eine zweite Formulierung gegenüber: die **Spaltenformulierung**. Eine **Spalte** ist der **Lebenslauf eines Stapels** (sein Inhalt zu Beginn jeder Periode), die Spalten eines Stapels sind die **Pfade in einem Stapelgraphen**, ein **Master** koppelt die Stapel. Die Demo **rechnet das live** auf kleinen Buchten, zeigt die Pfade der Mini-Bucht und misst vorberechnet, **wie groß der Stapelgraph wird**, **wie stark die Schranke ist**, **wie viele Spalten reichen** und **wann Branch and Price verzweigen müsste**.

## Warum dieses Problem

Die LP-Schranke eines Modells entscheidet, wie viel eine Suche oder ein Branch-and-Bound beschneiden kann. Die Spaltenformulierung ist der klassische Weg zu einer **stärkeren** Schranke (Dantzig-Wolfe): Der Master optimiert über die konvexe Hülle der ganzzahligen Stapel-Pfade; die LP-Schranke war in allen gemessenen Buchten **nicht schwächer** als die des kompakten Modells (ein Beweis, dass das für diese Konstruktion so sein muss, liegt nicht vor). Hier die Messung, ob das beim Umstauen trägt: **Ja für die Schranke** (bei 3 × 3 beweist schon der Wurzelknoten das Optimum in 39 von 40 Buchten dieser Stichprobe gegen 31 mit dem kompakten LP; bei anderen Buchten seltener, etwa in 9 von 10), **nein für die Größe**: Der Stapelgraph ist im Median ab etwa 10 Containern größer als das kompakte Modell und wächst dann schnell (bis 12 Container gemessen), und das Preisproblem (ein kürzester Pfad im ausgeschriebenen Graphen) wächst mit der Stapelhöhe exponentiell. Die Hypothese der Gliederung („starke Untergrenzen, hoher Aufwand je Knoten“) trifft zu.

## Modell

**Eigene Konstruktion** in der Idee der Spaltenformulierungen für Stapelprobleme, kein Nachbau einer Veröffentlichung. Die Idee, Spalten als Zeitpläne einzelner Stapel zu nehmen und die Stapel über Bilanz- und Zeitbedingungen zu koppeln, entspricht van Brink und van der Zwaan (Premarshalling, arXiv 1406.7107, Volltext gelesen); dort ist das Preisproblem polynomial (maximale unabhängige Menge in einem Kreisgraphen), das ist für das Umstauen **nicht** hergeleitet. Zehendner und Feillet behandeln das Umstauen mit Branch and Price; von ihnen ist nur das Abstract gelesen, ihr Modell ist weder nachgebaut noch beschrieben.

- **Perioden:** Periode *t* ist der Abruf des Containers *t* (wie in Stück 7); die Umlagerungen der Periode geschehen davor (restricted: nur Container über *t* im Stapel von *t*).
- **Spalte:** Liegt *t* im Stapel, gehen alle Container darüber ab (oben zuerst) und *t* wird abgerufen; sonst kommt eine geordnete Liste von Containern *n* > *t* hinzu, soweit Platz ist (Höchsthöhe = Lagen + Platz, Standard 2). Kosten: die Zahl der Zugänge.
- **Stapelgraph:** Knoten (Periode, Inhalt), Kanten die Perioden-Schritte; die Spalten eines Stapels sind die Quelle-Senke-Pfade.
- **Master:** (P) je Stapel genau ein Pfad; (B) **Bilanz**: je Container und Periode Zugänge = Abgänge, summiert über die Stapel; (O) **Ordnung**: kommen zwei Container im selben Stapel an und ging der eine vor dem anderen ab, dann in dieser Reihenfolge (ersetzt die LIFO-Nebenbedingung aus Stück 7). Mit ganzzahligen Pfaden **exakt**.
- **Pfadfluss:** eine Variable je Kante; dieselbe LP wie der Master mit **allen** Spalten.
- **Spaltengenerierung:** Start mit der Regel der engsten Passung (Stück 1), Master mit HiGHS (`scipy.optimize.milp`/`linprog`), **Preisproblem** = kürzester Pfad je Stapel mit den Dualwerten; Pfade mit negativen reduzierten Kosten kommen hinzu.
- **Wurzelknoten:** Der aufgerundete LP-Wert ist eine untere Schranke; löst man den Master mit den erzeugten Spalten ganzzahlig („Preis und Verzweige“) und trifft den aufgerundeten LP-Wert, ist das Optimum **bewiesen**. Sonst müsste verzweigt werden (**nicht gebaut**, die Fälle werden gezeigt).

## Methodik

- **Live:** Die Spaltengenerierung wird nur gerechnet, wenn die Stapelgraphen zusammen höchstens **60 000 Kanten** haben (bei Platz 2 rund 10 bis 12 Container, bei mehr Platz weniger); der Aufbau bricht bei dieser Zahl ab. Darüber zeigt die Demo die Größe des kompakten Modells und „nicht gerechnet“. Der ganzzahlige Pfadfluss läuft mit 60 s Zeitlimit; ohne Beweis behauptet die Demo keinen Wert.
- **Vorberechnet** (`stg_bands.json`, erzeugt von `generate_precomputed.py` in mehreren Prozessen; die Zelle 4 × 3 ist die langsamste): Größe der Stapelgraphen und Stärke der Schranke in sechs Zellen (3 × 2, 4 × 2, 3 × 3, 5 × 2, 4 × 3, 3 × 4), Spaltengenerierung in fünf (ohne 3 × 4: dort nur der volle Pfadfluss), die Gegenprobe ohne die Ordnungsbedingung in drei. **Dieselben festen Buchten wie in Stück 4 bis 7** (Seeds ab 0, Platz 2).
- **Alle Zeiten sind Einzelmessungen** (Windows, ein Lauf) und schwanken. Die Spaltengenerierung und das Preisproblem laufen in Python, die LP-Löser (HiGHS) in C++: **Sekunden sind kein reines Maß der Verfahren.**
- **Abschnitte der App:** Ergebnis (live); die Mini-Bucht von Hand (Pfade je Stapel); wie groß der Stapelgraph wird; wie stark die Schranke ist; wie viele Spalten reichen; wann Branch and Price verzweigen müsste; warum der Master die Ordnungsbedingung braucht; Grenzen; mathematische Formulierung.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen sind Messungen an den festen Buchten 0 bis (Zahl der Buchten − 1) je Zelle bei Platz 2, nachgerechnet in `tests/test_claims.py` und `tests/test_presets.py`. **Zeiten sind die gespeicherten Einzelmessungen.**

**A: Größe des Stapelgraphen** (Summe über die Stapel einer Bucht; Median / Maximum über die Buchten; zum Vergleich die Variablen des kompakten Modells aus Stück 7)

| Zelle (Container), Buchten | Knoten Median | Kanten Median / Maximum | kompaktes Modell (Variablen) | Kanten / Variablen | Aufbau Median |
|---|---|---|---|---|---|
| 3 × 2 (6), 100 | 88 | 158 / 304 | 1 692 | 0,09 | 0,9 ms |
| 4 × 2 (8), 60 | 1 020 | 2 705 / 3 516 | 5 952 | 0,45 | 0,01 s |
| 3 × 3 (9), 40 | 2 109 | 5 464 / 20 671 | 6 075 | 0,90 | 0,04 s |
| 5 × 2 (10), 12 | 5 060 | 15 560 / 20 648 | 15 500 | 1,00 | 0,11 s |
| 3 × 4 (12), 6 | 88 542 | 307 003 / 549 150 | 15 660 | 19,6 | 2,3 s |
| 4 × 3 (12), 8 | 26 829 | 91 338 / 394 444 | 21 360 | 4,28 | 0,71 s |

**B: Wie stark ist die Schranke?** (LP-Wert der Spaltenformulierung am Wurzelknoten gegen den des kompakten Modells aus Stück 7 und gegen das Optimum; Anzahl der Buchten)

| Zelle (Buchten) | Spalten-LP = Optimum | kompaktes LP = Optimum | Spalten-LP strikt stärker / schwächer | Optimum − LP, Spalten (Median, Maximum) | Optimum − LP, kompakt (Median, Maximum) | im Wurzelknoten bewiesen: Spalten / kompakt |
|---|---|---|---|---|---|---|
| 3 × 2 (100) | 100 | 100 | 0 / 0 | 0, 0 | 0, 0 | 98 / 98 |
| 4 × 2 (60) | 60 | 60 | 0 / 0 | 0, 0 | 0, 0 | 60 / 60 |
| 3 × 3 (40) | 37 | 31 | **8** / 0 | 0, 1 | 0, 2 | **39 / 31** |
| 5 × 2 (12) | 12 | 12 | 0 / 0 | 0, 0 | 0, 0 | 12 / 12 |
| 4 × 3 (8) | 7 | 5 | **3** / 0 | 0, 0,5 | 0, 1 | **8 / 5** |
| 3 × 4 (6) | 4 | 3 | **3** / 0 | 0, 0,5 | 0,5, 2 | nicht gerechnet |

Die Schranke war in **keiner** der gemessenen Buchten schwächer (14 von 226 gespeicherten Buchten strikt stärker); die Dantzig-Wolfe-Theorie legt das nahe, für diese Konstruktion (Bilanz- und Ordnungsbedingungen) ist es nicht bewiesen. „Im Wurzelknoten bewiesen“: aufgerundeter LP-Wert = Wert der Lösung aus den erzeugten Spalten.

**C: Wie viele Spalten braucht die Generierung?** (Wurzelknoten, Python; Zeiten schließen den Aufbau des Stapelgraphen ein)

| Zelle (Buchten) | Iterationen Median / Maximum | Spalten Median / Maximum | Spalten / Kanten (Median) | Wurzel ganzzahlig | Lösung aus Spalten = Optimum | Zeit Median / Maximum | Anteil Preisproblem |
|---|---|---|---|---|---|---|---|
| 3 × 2 (100) | 3 / 9 | 5 / 25 | 2,6 % | 97 | 98 | 0,02 s / 0,08 s | 14 % |
| 4 × 2 (60) | 3 / 12 | 8 / 42 | 0,46 % | 58 | 60 | 0,06 s / 0,32 s | 62 % |
| 3 × 3 (40) | 7 / 38 | 19 / 107 | 0,51 % | 36 | 40 | 0,54 s / 5,1 s | 85 % |
| 5 × 2 (12) | 4 / 15 | 14 / 63 | 0,10 % | 12 | 12 | 0,53 s / 1,6 s | 82 % |
| 4 × 3 (8) | 29,5 / 96 | 116 / 378 | 0,05 % | 7 | 8 | 19 s / 101 s | 95 % |

Der ganzzahlige Pfadfluss über **alle** Spalten braucht bei 3 × 4 (6 Buchten) im Median 5,4 s, höchstens 26,9 s (HiGHS).

**D: Wann müsste Branch and Price verzweigen?** In 3 von 220 Buchten der Zellen 3 × 2 bis 4 × 3 beweist der Wurzelknoten das Optimum nicht:

| Zelle | Bucht | Optimum | Spalten-LP | Lösung aus den erzeugten Spalten |
|---|---|---|---|---|
| 3 × 2 | 6 | 4 | 4 | 5 |
| 3 × 2 | 10 | 4 | 4 | 5 |
| 3 × 3 | 7 | 8 | 7 | 8 |

Zwei Ursachen: Bei 3 × 3, Bucht 7, liegt der LP-Wert **unter** dem Optimum (echte Lücke, beide LP-Schranken 7); bei den beiden 3 × 2-Buchten ist der LP-Wert **gleich** dem Optimum, aber die erzeugten Spalten enthalten die optimale Lösung nicht.

**E: Warum braucht der Master die Ordnungsbedingung (O)?** (ganzzahliger Pfadfluss ohne (O), geprüft gegen die Suche und durch Nachspielen)

| Zelle (Buchten) | Optimum zu klein | nicht spielbar | falsch insgesamt |
|---|---|---|---|
| 3 × 2 (100) | 0 | 4 | 4 |
| 4 × 2 (60) | 0 | 4 | 4 |
| 3 × 3 (40) | 9 | 17 | 17 |

| Frage | Befund |
|---|---|
| **Ist die Formulierung korrekt?** | Der ganzzahlige Pfadfluss trifft das Optimum der Breitensuche und der Suche in allen geprüften Buchten (`tests/test_oracle_stapelgraph_spalten_umstauen.py`: alle 3 × 2, 4 × 2, 3 × 3); jede Lösung wird zu einer Hubfolge zusammengesetzt und mit einem eigenen Simulator nachgespielt. Mini-Bucht: Optimum 2, Gegenbeispiel aus Stück 1: 4, drei Blocker über der 1: 8. |
| **Ist die Schranke stärker?** | Nie schwächer, oft stärker: bei 3 × 3 in 8 von 40 Buchten strikt, bei 4 × 3 in 3 von 8, bei 3 × 4 in 3 von 6; bei 3 × 2, 4 × 2 und 5 × 2 sind beide Schranken gleich dem Optimum. |
| **Wie viele Spalten?** | Wenige im Verhältnis zu den Kanten: im Median 19 von 5 464 Kanten bei 3 × 3 (0,5 %), 116 von 91 338 bei 4 × 3 (0,05 %). |
| **Wie wächst der Stapelgraph?** | Im Median kleiner als das kompakte Modell bis 9 Container (Verhältnis 0,09 bis 0,90), bei 10 Containern gleich groß (1,00 bei 5 × 2), darüber größer (4,3 bei 4 × 3, 19,6 bei 3 × 4); einzelne 3 × 3-Buchten sind bis 3,4-fach größer. Bei 3 × 3 mit Höchsthöhe 5 hat der größte Stapelgraph in der Vormessung rund 2,6 Millionen Pfade, aber nur 5 274 Zustände. |
| **Wo steckt die Zeit?** | Im Preisproblem: 82 bis 95 % ab 9 Containern (kürzester Pfad im ausgeschriebenen Graphen). Die Spaltengenerierung ist hier **langsamer** als das kompakte ILP aus Stück 7 (4 × 3: Median 19 s gegen 1,4 s), aber Python gegen C++. |
| **Ist Verzweigen nötig?** | Bei kleinen Buchten selten, bei 3 × 3 bereits in rund jeder zehnten Bucht (in 3 von 220 gespeicherten Buchten; eine Nachprüfung mit 160 Buchten der Zelle 3 × 3 fand 15; zwei der drei gespeicherten mit LP = Optimum, aber ohne die optimale Lösung im Spaltenvorrat). Echtes Branch and Price ist **nicht** gebaut. |
| **Braucht der Master (O)?** | Ja: Ohne die Ordnungsbedingung ist bei 3 × 3 das Optimum in 9 von 40 Buchten zu klein und in 17 die Lösung nicht als Hubfolge spielbar. |
| **Die Mini-Bucht** | (1, 4), (5, 2), (6, 3), Höchsthöhe 4: 133 Knoten und 264 Kanten (das kompakte Modell hat 1 692 Variablen), 4 Iterationen, 7 Spalten, Wurzel-LP 2 und ganzzahlig. Das Preset „Die Mini-Bucht“ ist dieselbe Bucht mit vertauschten Stapeln und braucht 6 Spalten. |

**Presets** (Eigenschaften in `tests/test_presets.py`): „Alltag“ (3 × 3, Bucht 12: 6 899 Kanten, 7 Iterationen, 19 Spalten, Optimum 5, im Wurzelknoten bewiesen), „Die Mini-Bucht“ (3 × 2, Bucht 223), „Die Schranke ist stärker“ (3 × 3, Bucht 27: kompaktes LP 5, Spalten-LP 6 gleich dem Optimum), „Verzweigen nötig“ (3 × 3, Bucht 7: LP 7, Optimum 8), „Zu groß für live“ (4 × 3, Bucht 0: Stapelgraphen mit rund 394 000 Kanten werden nicht gerechnet, die Suche löst die Bucht, Optimum 10).

**Korrektur gegenüber dem Plan:** Der Messlauf der Demo liefert dieselben Zählungen wie die Vormessung (Größen, Stärke der Schranke, Iterationen, Spalten, Buchten ohne Beweis). Die **Zeiten** weichen ab (Einzelmessungen auf anderer Last): Median der Wurzelzeit bei 3 × 3 0,54 s (Plan 0,70 s), bei 5 × 2 0,53 s (0,81 s), bei 4 × 3 19 s (30,5 s, Maximum 101 s statt 124 s). Der Anteil des Preisproblems liegt ab 9 Containern bei **82 bis 95 %** (Plan: 75 bis 92 %). Die Mini-Bucht der Hand-Sektion hat 7 Spalten, die des Presets (vertauschte Stapel) 6.

## Ehrliche Grenzen

- **Kein Verzweigen.** Die Demo löst den Wurzelknoten und zeigt, wann das Optimum dort nicht bewiesen ist; echtes Branch and Price ist nicht gebaut. „Selten nötig“ gilt für 3 × 2 und 4 × 2; bei 3 × 3 beruht es auf einer günstigen Stichprobe (1 von 40, in einer Nachprüfung mit 160 Buchten 15).
- **Das Preisproblem ist ein kürzester Pfad im ausgeschriebenen Stapelgraphen** und damit exponentiell in der Stapelhöhe. Ein polynomiales Preisproblem wie bei van Brink und van der Zwaan wurde für das Umstauen **nicht** hergeleitet; ob es eines gibt, ist offen.
- **Zeiten sind Einzelmessungen** (Python gegen C++, ein Lauf, eine Windows-Maschine). Der Vergleich 19 s gegen 1,4 s mischt Sprachen.
- **Kleine Zellen:** 4 × 3 mit 8 und 3 × 4 mit 6 Buchten; Aussagen dort sind grob (3 von 8, 3 von 6).
- **Eigene Konstruktion.** Zehendner und Feillet sind nur im Abstract gelesen; die Aussage, dass ihr Verfahren kleine und mittlere Instanzen löst, ist die des Abstracts.
- **Nur bis 60 000 Kanten live;** darüber „nicht gerechnet“.
- **Nur restricted, nur volle Buchten, Platz 2 in den Tabellen,** Zufallsbuchten aus der Zufallsfolge von Python. Mit anderer Hubmenge (Stück 3) oder anderer Füllung ändern sich Größe und Schranke.

## Verifikation

- **Kern:** Stapelgraph eines Stapels von Hand (Kanten, Zugangslisten), Mini-Bucht (133 Knoten, 264 Kanten), Gegenbeispiel (152 / 304), drei Blocker (1 216 / 3 226), ganzzahliger Pfadfluss und Spaltengenerierung an Handwerten (Iterationen, Spalten), Kantenlimit des Aufbaus, Eingabeprüfung, Matrizen des Pfadflusses, Startlösung der Heuristik.
- **Orakel:** Pfadfluss gegen eine **Breitensuche** über alle Zustände (alle 3 × 2) und gegen die Suche, jede Lösung in einem **eigenen Simulator** nachgespielt; Größe und Pfadzahl gegen eine **zweite Aufzählung**; **Zertifikat**: die optimale Hubfolge der Breitensuche, in Kantenvariablen übersetzt, erfüllt jede Kopplungsbedingung mit dem Optimum als Zielwert, ein beschädigter Punkt verletzt eine; die Spaltengenerierung liefert denselben LP-Wert wie der volle Pfadfluss; ohne (O) wird der Master falsch.
- **Eigenschaften:** Spalten-LP ≥ kompaktes LP, LP ≤ Optimum, Untergrenze aus Stück 2 ≤ LP-Wert, sortierte Bucht hat Optimum 0 und ganzzahlige Wurzel.
- **Zahlen im README:** jede Zahl der Befunde in `tests/test_claims.py` (gespeicherte Bänder); zwei kleine Zellen (Größe/Schranke 3 × 2, Gegenprobe 3 × 2) werden frisch nachgerechnet, ohne Zeiten.
- **Verdikte:** reine Funktionen, jede Schwelle und jede genannte Zahl an von Hand gesetzten Werten (`tests/test_verdicts.py`).
- **Presets und Oberfläche:** AppTest-Rauchtest (jeder Button, jeder Regler an Minimum und Maximum), Inhalt (Kennzahlen je Preset, Tabellenzeilen), Layout, Footer, Laufzeit-Importe (`scipy`, `numpy`), Abbildungen (Farben, gesperrte Achsen, logarithmische Achsen ohne `add_hline`).

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App (Aufbau nach DEMO-PLAYBOOK §2) |
| `generate_precomputed.py` | erzeugt `stg_bands.json` (Größe, Schranke, Spalten, Gegenprobe) |
| `requirements-dev.txt` | Laufzeit plus pytest |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt): streamlit, plotly, scipy, numpy |
| `stg_algorithm.py` | Suche (IDA\* mit Untergrenze und Merken) und Simulator der Umlagerungen |
| `stg_bands.json` | vorberechnete Kennzahlen der festen Buchten je Zelle |
| `stg_compact.py` | das kompakte Modell aus Stück 7 (Größe, LP-Wert) zum Vergleich |
| `stg_constants.py` | Regler-Grenzen, Limits, Zellen, Farben, Sonderbuchten, Presets |
| `stg_evaluation.py` | Analyse einer Bucht, Stichproben, Verdikte (reine Funktionen) |
| `stg_graph.py` | Stapelgraph, gekoppelter Master, Pfadfluss, Spaltengenerierung |
| `stg_layout.py` | Fester Kopf (Stylesheet) |
| `stg_presets.py` | Permalink (Begrenzen), Presets (Schnellstart in der Seitenleiste), Zufalls-Seed-Button |
| `stg_scenario.py` | Buchten (volle Buchten, Zufallsbuchten) |
| `stg_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `tests/` | Handrechnung, Orakel, Zertifikat, Gegenprobe, Randfälle, Behauptungen, Verdikte, Presets, Abbildungen, AppTest, Layout, Footer, Laufzeit-Importe |

## Bewusst nicht umgesetzt

- **Echtes Verzweigen (Branch and Price)** und ein **polynomiales Preisproblem.** Das Premarshalling-Stück 11 der Reihe behandelt das publizierte Verfahren.
- **Das Modell von Zehendner und Feillet** (Volltext nicht gelesen).
- **Eine Zeitmessung in der CI:** Zeiten schwanken.
- **Die Spaltengenerierung live jenseits von 60 000 Kanten.**
- **PDF-Export:** nicht vorgesehen.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

107 Tests, rund 240 Sekunden (eine Messung unter Windows; kleine Spaltengenerierungen werden live gerechnet).

Gebaut mit Streamlit, Plotly, SciPy (HiGHS).

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html).
