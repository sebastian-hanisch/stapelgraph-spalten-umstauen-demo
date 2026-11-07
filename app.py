"""Die Spaltenformulierung: Stapelgraph und Spaltengenerierung beim Umstauen - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Stück 8 der Reihe „Umstauen: Untergrenze und Suche“. Stück 7 hat das kompakte, zeitindizierte Modell gemessen. Hier die Spaltenformulierung: Eine Spalte ist der Lebenslauf eines
Stapels, die Spalten eines Stapels sind die Pfade im Stapelgraphen, ein Master koppelt die Stapel. Die Demo rechnet die Spaltengenerierung live auf kleinen Buchten, zeigt die Pfade
der Mini-Bucht und misst vorberechnet, wie stark die Schranke ist, wie viele Spalten die Generierung braucht und wie schnell der Stapelgraph wächst.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import stg_constants as C
import stg_graph as G
from stg_algorithm import replay
from stg_evaluation import (
    Settings,
    analyse,
    cell_key,
    iter_text,
    load_bands,
    lp_text,
    ms_text,
    num,
    num_f,
    path_rows,
    percent_text,
    result_rows,
    sec_text,
    time_text,
    verdict_bay,
    verdict_columns,
    verdict_fix,
    verdict_size,
    verdict_strength,
)
from stg_layout import dunkles_design, kopf_css
from stg_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)
from stg_visualization import build_bay, build_columns, build_size, build_stack_sizes, build_strength

st.set_page_config(page_title="Spaltenformulierung – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _analysis(settings):
    return analyse(settings)


@st.cache_data(show_spinner=False)
def _bands():
    return load_bands()


@st.cache_data(show_spinner=False)
def _hand():
    """Die Mini-Bucht: Stapelgraphen, Spaltengenerierung, ganzzahliger Pfadfluss, Pfade und nachgespielte Hubfolge; dazu das Gegenbeispiel aus Stück 1."""
    out = []
    for bay, h in ((C.MINI_BAY, C.MINI_HEIGHT), (C.COUNTER_BAY, C.COUNTER_HEIGHT)):
        cp = G.build_coupled(bay, h)
        flow = G.solve_flow(cp, True, 60)
        cg = G.column_generation(bay, cp)
        out.append({"nodes": cp.nodes, "arcs": cp.arcs, "stack_sizes": cp.stack_sizes(), "flow": flow, "cg": cg, "rows": path_rows(cp, flow.paths),
                    "hubs": replay(bay, h, G.paths_to_moves(cp, flow.paths))})
    return out


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in stg_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🕸️ Die Spaltenformulierung: Stapelgraph und Spaltengenerierung")
st.markdown(
    """
Stück 7 hat das **kompakte Modell** gemessen. Hier die **Spaltenformulierung**: Eine **Spalte** ist der **Lebenslauf eines Stapels** (sein Inhalt in jeder Periode), die Spalten eines Stapels sind die **Pfade in einem Stapelgraphen**, ein **Master** koppelt die Stapel. Ihre LP-Schranke ist **nie schwächer** als die des kompakten Modells, die **Spaltengenerierung** braucht nur **wenige Spalten** – aber der Stapelgraph wächst schnell. Die Demo **rechnet das live** auf kleinen Buchten, zeigt die Pfade der Mini-Bucht und misst, **wie stark** die Schranke ist, **wie viele Spalten** reichen und **wann Branch and Price verzweigen müsste**.

Weiter unten: die Abschnitte **🔬 Experiment** (die Mini-Bucht von Hand, wie groß der Stapelgraph wird, wie stark die Schranke ist, wie viele Spalten reichen, wann verzweigt werden müsste, warum die Ordnungsbedingung nötig ist), **🚧 Wo die Annahmen enden** und der Expander **📐 Mathematische Formulierung**. Dies ist das achte Stück der Reihe „Umstauen: Untergrenze und Suche“.
"""
)

with st.expander("So funktioniert die Spaltenformulierung", expanded=True):
    st.markdown(
        """
1. **Spalte:** der Inhalt eines Stapels zu Beginn jeder Periode *t* (Periode *t* = Abruf des Containers *t*). Liegt *t* im Stapel, gehen alle Container darüber ab (oben zuerst) und *t* wird abgerufen; sonst kommt eine geordnete Liste von Containern hinzu, soweit Platz ist. Kosten: die Zahl der Zugänge.
2. **Stapelgraph:** Knoten sind (Periode, Inhalt), Kanten die Perioden-Schritte; die Spalten eines Stapels sind genau die Pfade von der Quelle zur Senke.
3. **Master:** je Stapel genau ein Pfad; je Container und Periode Zugänge = Abgänge (**Bilanz**); kommen zwei Container im selben Stapel an und ging der eine vor dem anderen ab, dann in dieser Reihenfolge (**Ordnung**).
4. **Pfadfluss:** eine Variable je Kante; dieselbe LP wie der Master mit **allen** Spalten.
5. **Spaltengenerierung:** Man startet mit wenigen Spalten (Regel der engsten Passung), löst den Master, berechnet für jeden Stapel den **kürzesten Pfad** im Stapelgraphen mit den Dualwerten (das **Preisproblem**) und fügt Pfade mit negativen reduzierten Kosten hinzu, bis keiner mehr da ist.
6. **Wurzelknoten:** Ist der aufgerundete LP-Wert gleich dem Wert der Lösung aus den erzeugten Spalten, ist das Optimum bewiesen. Sonst müsste **Branch and Price** verzweigen; das ist hier **nicht** gebaut, die Fälle werden gezeigt.
        """
    )

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Bucht**")
    stacks = st.slider("Stapel", *bounds("stacks_slider"), key="stacks_slider", help="Wie viele Stapel die Bucht hat.")
    layers = st.slider("Lagen je Stapel", *bounds("layers_slider"), key="layers_slider", help="So viele Container stehen anfangs auf jedem Stapel.")
    extra = st.slider("Platz (Lagen über der Anfangshöhe)", *bounds("extra_slider"), key="extra_slider",
                      help=f"Höchsthöhe = Lagen + Platz. Standard 2. Die vorberechneten Tabellen gelten für Platz 2. Die Spaltenformulierung wird live nur gerechnet, wenn die Stapelgraphen höchstens {num(C.LIVE_MAX_ARCS)} Kanten haben (rund 9 bis 10 Container).")
    seed = st.number_input("Bucht-Nummer (Seed)", *bounds("seed_input"), key="seed_input", step=1, help="Die Nummer bestimmt, wie die Abrufnummern auf die Plätze verteilt sind.")
    st.button("🎲 Neue Bucht würfeln", width="stretch", on_click=randomize_seed)

sync_query_params({"stacks_slider": int(stacks), "layers_slider": int(layers), "extra_slider": int(extra), "seed_input": int(seed)})

settings = Settings(int(stacks), int(layers), int(extra), int(seed))
with st.spinner(f"Baue die Stapelgraphen (höchstens {num(C.LIVE_MAX_ARCS)} Kanten) und rechne die Spaltengenerierung …"):
    a = _analysis(settings)

# --- Ergebnis ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ergebnis")
cg = a.cg
m1, m2, m3, m4 = st.columns(4)
if a.graph is None:
    m1.metric("Stapelgraphen (Kanten)", "nicht gerechnet", delta=f"mehr als {num(C.LIVE_MAX_ARCS)}", delta_color="off", help="Der Bau bricht bei dieser Kantenzahl ab.")
    m2.metric("Spalten-LP (Wurzel)", "–", delta=f"kompaktes Modell: {num(a.compact_size[0])} Variablen", delta_color="off")
    m3.metric("Erzeugte Spalten", "–")
else:
    m1.metric("Stapelgraphen (Kanten)", num(a.graph[1]), delta=f"{num(a.graph[0])} Knoten", delta_color="off", help="Summe über alle Stapel.")
    m2.metric("Spalten-LP (Wurzel)", lp_text(cg.value), delta=f"kompaktes LP {lp_text(a.compact_lp)}", delta_color="off", help="Schranke der Spaltenformulierung am Wurzelknoten; darunter die des kompakten Modells aus Stück 7.")
    m3.metric("Erzeugte Spalten", num(cg.columns), delta=f"{iter_text(cg.iterations)}, von {num(cg.arcs)} Kanten", delta_color="off", help="Inklusive der Startspalten.")
m4.metric("Optimum", "nicht bewiesen" if a.optimum is None else a.optimum, delta=f"Untergrenze {a.lower}, Bucht {settings.stacks} × {settings.layers}", delta_color="off")
st.plotly_chart(build_bay(a.bay, a.height, target=min(c for s in a.bay for c in s)), width="stretch", key="chart_bay")
st.caption("Rot: blockierende Container (liegen über einem früher abzurufenden), grün: der nächste Abruf, grau-blau: alle übrigen.")
table = ["| Verfahren | Wert | Aufwand |", "|---|---|---|"]
for r in result_rows(a):
    table.append(f"| {r['name']} | {r['value']} | {r['effort']} |")
st.markdown("\n".join(table))
st.caption("Zeiten sind Einzelmessungen auf dem Rechner dieser Sitzung und schwanken. Die Spaltengenerierung läuft in Python, die LP-Löser (HiGHS) in C++.")
if a.graph is not None:
    st.plotly_chart(build_stack_sizes(list(a.stack_sizes)), width="stretch", key="chart_stack_sizes")

# --- Kernfrage -----------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage: Trägt die Spaltenformulierung?")
kind, text = verdict_bay(a)
getattr(st, kind)(text)

st.markdown("---")

# --- Experiment: die Mini-Bucht von Hand ----------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment: Die Spaltenformulierung der Mini-Bucht von Hand")
mini, counter = _hand()
st.caption("3 Stapel mit je 2 Containern, Höchsthöhe 4, von unten nach oben (1, 4), (5, 2), (6, 3): nur die 4 blockiert (Untergrenze 1). Die Stapelgraphen haben zusammen "
           f"**{num(mini['nodes'])} Knoten** und **{num(mini['arcs'])} Kanten** (das kompakte Modell aus Stück 7 hat 1 692 Variablen); die Spaltengenerierung braucht {iter_text(mini['cg'].iterations)} und "
           f"{mini['cg'].columns} Spalten, die Wurzel ist {'ganzzahlig' if mini['cg'].integral else 'gebrochen'} (Wert {lp_text(mini['cg'].value)}).")
st.plotly_chart(build_bay(C.MINI_BAY, C.MINI_HEIGHT, target=1), width="stretch", key="chart_mini")
pt = ["| Stapel | Periode | Inhalt zu Beginn | Zugänge | Abgänge |", "|---|---|---|---|---|"]
for r in mini["rows"]:
    pt.append(f"| {r['stack']} | {r['period']} | {r['content']} | {r['arrivals']} | {r['departures']} |")
st.markdown("\n".join(pt))
st.success(f"Optimum {round(mini['flow'].value)}: Die Pfade der drei Stapel (ganzzahliger Pfadfluss) ergeben zusammengesetzt eine Hubfolge, die der Simulator der Suche nach den Regeln nachspielt "
           f"({mini['hubs']} Hübe). In der Periode des Abrufs der 1 geht die 4 vom ersten Stapel ab und kommt in einem anderen an; später muss sie noch einmal weg. Welche der gleichwertigen Lösungen der Löser liefert, kann je Version wechseln.")
cc = counter["cg"]
st.markdown(f"**Das Gegenbeispiel aus Stück 1** ((3, 6), (2, 4), (1, 5), Höchsthöhe 4): Stapelgraphen mit {num(counter['nodes'])} Knoten und {num(counter['arcs'])} Kanten, Spalten-LP {lp_text(cc.value)} (gleich dem Optimum "
            f"{round(counter['flow'].value)}), aber die Lösung aus den erzeugten Spalten kostet {cc.pool_value}: Der **Wurzelknoten kann das Optimum nicht beweisen**, Branch and Price müsste verzweigen "
            f"(der ganzzahlige Pfadfluss über alle Spalten liefert {round(counter['flow'].value)}).")

st.markdown("---")

# --- Experiment: Wie groß wird der Stapelgraph? ---------------------------------------------------------------------------------------------------

bands = _bands()
zellen = bands["zellen"]
st.subheader("🔬 Experiment: Wie groß wird der Stapelgraph?")
st.caption("Je Zelle feste Buchten (Platz 2, dieselben wie in Stück 4 bis 7), vorberechnet (`generate_precomputed.py`). Kanten der Stapelgraphen zusammen, Median / Maximum über die Buchten, "
           "gegen die Variablen des kompakten Modells aus Stück 7.")
cells_a = {f"{s_} × {l_}": zellen[cell_key(s_, l_)] for s_, l_, _ in C.SIZE_CELLS}
ta = ["| Zelle (Container), Buchten | Knoten Median | Kanten Median / Maximum | kompaktes Modell (Variablen) | Aufbau der Graphen Median |", "|---|---|---|---|---|"]
for name, c in sorted(cells_a.items(), key=lambda kv: (kv[1]["containers"], kv[1]["compact_vars"])):
    ta.append(f"| {name} ({c['containers']}), {c['n']} | {num_f(c['nodes']['median'])} | {num_f(c['arcs']['median'])} / {num(c['arcs']['max'])} | {num(c['compact_vars'])} | {time_text(c['build_s']['median'])} |")
st.markdown("\n".join(ta))
st.plotly_chart(build_size(cells_a), width="stretch", key="chart_size")
here = zellen.get(cell_key(settings.stacks, settings.layers))
st.markdown(f"**Zelle {settings.stacks} × {settings.layers} (Ihre Einstellung)**" + ("" if settings.extra == C.DEFAULT_EXTRA else f", Tabellen gelten für Platz {C.DEFAULT_EXTRA}, hier ist Platz {settings.extra} eingestellt") + ":")
if here is None:
    st.info(f"Für {settings.stacks} × {settings.layers} wurden die Stapelgraphen nicht vorberechnet (zu groß); die Tabelle zeigt die Zellen, die gerechnet wurden.")
else:
    kind, text = verdict_size(here, f"{settings.stacks} × {settings.layers}")
    getattr(st, kind)(text)

st.markdown("---")

# --- Experiment: Wie stark ist die Schranke? -------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment: Wie stark ist die Schranke?")
st.caption("LP-Wert der Spaltenformulierung (Wurzelknoten) gegen den des kompakten Modells und gegen das Optimum; Zahl der Buchten. „Im Wurzelknoten bewiesen“: aufgerundeter LP-Wert = Wert der Lösung aus den erzeugten Spalten.")
tb = ["| Zelle (Buchten) | LP trifft das Optimum: Spalten / kompakt | Spalten-LP strikt stärker / schwächer | Optimum − LP, Spalten (Median, Maximum) | Optimum − LP, kompakt (Median, Maximum) | im Wurzelknoten bewiesen: Spalten / kompakt |", "|---|---|---|---|---|---|"]
for s_, l_, n_ in C.SIZE_CELLS:
    c = zellen[cell_key(s_, l_)]
    proven = f"{c['cg']['proven']} / {c['cg']['proven_compact']} von {c['cg']['n']}" if "cg" in c else "nicht gerechnet"
    tb.append(f"| {s_} × {l_} ({c['n']}) | {c['cols_equal']} / {c['compact_equal']} | {c['stronger']} / {c['weaker']} | {num_f(c['gap_cols']['median'])}, {lp_text(c['gap_cols']['max'])} | "
              f"{num_f(c['gap_compact']['median'])}, {lp_text(c['gap_compact']['max'])} | {proven} |")
st.markdown("\n".join(tb))
st.plotly_chart(build_strength(cells_a), width="stretch", key="chart_strength")
if here is not None:
    st.markdown(f"**Zelle {settings.stacks} × {settings.layers} (Ihre Einstellung):**")
    kind, text = verdict_strength(here, f"{settings.stacks} × {settings.layers}")
    getattr(st, kind)(text)

st.markdown("---")

# --- Experiment: Wie viele Spalten braucht es? -----------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment: Wie viele Spalten braucht die Generierung?")
st.caption("Spaltengenerierung am Wurzelknoten (Python): Iterationen, erzeugte Spalten gegen Kanten, Anteil des Preisproblems an der Zeit. Zeiten sind Einzelmessungen; 3 × 4 wurde nur mit dem vollen Pfadfluss gerechnet.")
tc = ["| Zelle (Buchten) | Iterationen Median / Maximum | Spalten Median / Maximum | Spalten / Kanten (Median) | Wurzel ganzzahlig | Lösung aus Spalten = Optimum | Zeit Median / Maximum | Anteil Preisproblem |", "|---|---|---|---|---|---|---|---|"]
for s_, l_, n_ in C.CG_CELLS:
    c = zellen[cell_key(s_, l_)]
    g = c["cg"]
    tc.append(f"| {s_} × {l_} ({g['n']}) | {num_f(g['iterations']['median'])} / {num(g['iterations']['max'])} | {num_f(g['columns']['median'])} / {num(g['columns']['max'])} | {percent_text(g['share'])} | "
              f"{g['integral']} | {g['pool_equal']} | {sec_text(g['seconds']['median'])} s / {sec_text(g['seconds']['max'])} s | {percent_text(g['price_share'])} |")
st.markdown("\n".join(tc))
st.plotly_chart(build_columns(cells_a), width="stretch", key="chart_columns")
if here is not None and "cg" in here:
    kind, text = verdict_columns(here, f"{settings.stacks} × {settings.layers}")
    getattr(st, kind)(text)

st.markdown("---")

# --- Experiment: Wann müsste verzweigt werden? ----------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment: Wann müsste Branch and Price verzweigen?")
st.caption("Buchten, in denen der Wurzelknoten das Optimum nicht beweist (aufgerundeter LP-Wert ungleich dem Wert der Lösung aus den erzeugten Spalten). Jede Bucht lässt sich mit dem Preset oder der Bucht-Nummer ansehen.")
tu = ["| Zelle | Bucht | Optimum | Spalten-LP | Lösung aus den erzeugten Spalten |", "|---|---|---|---|---|"]
count = 0
for s_, l_, n_ in C.CG_CELLS:
    for u in zellen[cell_key(s_, l_)]["cg"]["unproven"]:
        tu.append(f"| {s_} × {l_} | {u['seed']} | {u['opt']} | {lp_text(u['value'])} | {u['pool']} |")
        count += 1
st.markdown("\n".join(tu))
total = sum(zellen[cell_key(s_, l_)]["cg"]["n"] for s_, l_, _ in C.CG_CELLS)
st.info(f"In {count} von {total} Buchten der Zellen 3 × 2 bis 4 × 3 beweist der Wurzelknoten das Optimum nicht. Zwei Ursachen: Der LP-Wert liegt unter dem Optimum (echte Lücke), oder der LP-Wert ist gleich dem Optimum, "
        "aber die erzeugten Spalten enthalten die optimale Lösung nicht (dann brauchte es mehr Spalten oder Verzweigen).")

st.markdown("---")

# --- Experiment: Warum die Ordnungsbedingung? --------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment: Warum braucht der Master die Ordnungsbedingung?")
fx = bands["korrektur"]
st.caption("Der ganzzahlige Pfadfluss ohne die Ordnungsbedingung (O): Wie oft ist das Optimum zu klein, wie oft lässt sich die Lösung nicht als Hubfolge nachspielen?")
tf = ["| Zelle (Buchten) | Optimum zu klein | nicht spielbar | falsch insgesamt |", "|---|---|---|---|"]
for s_, l_, n_ in C.FIX_CELLS:
    c = fx[cell_key(s_, l_)]
    tf.append(f"| {s_} × {l_} ({c['n']}) | {c['smaller']} | {c['unplayable']} | {c['wrong']} |")
st.markdown("\n".join(tf))
kind, text = verdict_fix(fx[cell_key(3, 3)], "3 × 3")
getattr(st, kind)(text)

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Kein Verzweigen** | Die Demo löst den Wurzelknoten und zeigt, wann das Optimum dort nicht bewiesen ist. Echtes Branch and Price ist nicht gebaut. | – |
| **Preisproblem im expliziten Stapelgraphen** | Ein kürzester Pfad im ausgeschriebenen Graphen ist exponentiell in der Containerzahl. Ein polynomiales Preisproblem (wie bei van Brink und van der Zwaan für das Premarshalling) ist für das Umstauen nicht hergeleitet. | – |
| **Zeiten sind Einzelmessungen** | Python (Generierung, Preisproblem) gegen C++ (HiGHS), ein Lauf, eine Windows-Maschine; die Zeiten stehen als Befund nur im Vergleich der Größenordnungen. | – |
| **Kleine Zellen** | 4 × 3 mit 8 und 3 × 4 mit 6 Buchten; Aussagen dort sind grob. | – |
| **Nur bis 60 000 Kanten live** | Darüber zeigt die App die Größe des kompakten Modells und „nicht gerechnet“. | – |
| **Eigene Konstruktion** | Das Modell ist keine Wiedergabe von Zehendner und Feillet (deren Volltext nicht gelesen), sondern eine eigene Spaltenformulierung in der Idee von van Brink und van der Zwaan. | – |
| **Nur restricted, nur volle Buchten, Platz 2 in den Tabellen** | Mit anderer Hubmenge (Stück 3) oder anderer Füllung ändern sich Größe und Schranke. | – |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Gegeben:** $W$ Stapel mit Höchsthöhe $H$, $N$ Container mit den Abrufnummern $1, \dots, N$ (kleiner = früher), die Anfangsbucht. Periode $t$ ist der Abruf des Containers $t$; die Umlagerungen der Periode geschehen davor (restricted: nur Container über $t$ im Stapel von $t$, einzeln von oben nach unten).

**Stapelgraph.** Für jeden Stapel $s$ ein Graph $G_s$. Knoten: $(t, B)$ mit dem Inhalt $B$ (Container von unten nach oben) zu Beginn der Periode $t$; Quelle: $(1, B_s^0)$; Senke: $(N+1, \emptyset)$. Kanten von $(t, B)$: *liegt $t$ in $B$*, genau eine Kante nach $(t+1, B')$, wobei $B'$ der Teil unter $t$ ist; **Abgänge** $D$ sind die Container über $t$ (oben zuerst); Kosten $0$. *Sonst* für jede geordnete Liste $A$ verschiedener Container $n > t$ mit $n \notin B$ und $|B| + |A| \le H$ eine Kante nach $(t+1, B \cdot A)$; **Zugänge** $A$; Kosten $|A|$. Eine **Spalte** ist ein Quelle-Senke-Pfad; seine Kosten sind die Zahl der Zugänge.

**Master.** Variable $f_{s,e} \ge 0$ je Kante $e$ von $G_s$.
- *Fluss (Pfad):* Flusserhaltung in jedem Knoten, ein Einheit von der Quelle zur Senke je Stapel.
- *Bilanz:* $\sum_{s,e:\, n \in A(e),\, t(e)=t} f_{s,e} = \sum_{s,e:\, n \in D(e),\, t(e)=t} f_{s,e}$ für jedes $(n,t)$.
- *Ordnung:* für jedes $(t, b_1, b_2)$: $\sum_{s,e:\, b_2 \prec_A b_1} f_{s,e} \le 1 - \sum_{s,e:\, b_1 \prec_D b_2} f_{s,e}$, dabei $b_2 \prec_A b_1$ „in der Zugangsliste von $e$ steht $b_2$ vor $b_1$“ und $b_1 \prec_D b_2$ „in der Abgangsliste von $e$ steht $b_1$ vor $b_2$“. Ging $b_1$ vor $b_2$ ab, darf kein Stapel beide in der Reihenfolge $b_2$, $b_1$ aufnehmen.
- *Ziel:* $\min \sum_{s,e} \text{Kosten}(e)\, f_{s,e}$.

Mit ganzzahligen $f$ ist das **exakt** (Optimum gleich dem der Suche). Seine LP-Relaxation ist die **Schranke der Spaltenformulierung**; sie ist nie schwächer als die des kompakten Modells aus Stück 7 (Dantzig-Wolfe: der Master optimiert über die konvexe Hülle der ganzzahligen Stapel-Pfade).

**Spaltengenerierung.** Master über die Pfade $P$ einer Teilmenge. Zu Dualwerten $\pi$ der Bilanz- und Ordnungsbedingungen und $\mu_s$ des Pfades ist der reduzierte Preis einer Kante ihre Kosten minus der Dualwerte ihrer Beiträge; das **Preisproblem** ist der kürzeste Pfad in $G_s$ (Knoten nach Periode geordnet, ein Durchlauf). Negativer Gesamtpreis minus $\mu_s$: der Pfad kommt hinzu. Ohne solchen Pfad ist der Master mit den erzeugten Spalten optimal für den ganzen Pfadfluss.

**Wurzelknoten.** Alle Kosten sind ganzzahlig, also ist $\lceil z_{LP} \rceil$ eine untere Schranke. Löst man den Master mit den erzeugten Spalten ganzzahlig (*Preis und Verzweige*) und gleicht der Wert $\lceil z_{LP} \rceil$, ist das Optimum bewiesen. Sonst müsste verzweigt werden (nicht gebaut).

**Literatur.** Das Umstauen mit Branch and Price behandeln Zehendner und Feillet (Mines Saint-Étienne, 2013, Tagungsband; Fachzeitschrift 2014; nur das Abstract gelesen). Die Idee, Spalten als Zugfolgen einzelner Stapel zu nehmen und die Stapel zu koppeln, entspricht van Brink und van der Zwaan, arXiv 1406.7107 (Premarshalling; Volltext gelesen). Die Spaltenformulierung hier ist eine eigene Konstruktion.
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html)."
)
