"""Kennzahlen, Verdikt-Logik, vorberechnete Tabellen. Reine Funktionen: die App ruft st.<Art>(Text), die Tests prüfen jede Zahl und jede Schwelle."""

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median

import stg_algorithm as A
import stg_compact as M
import stg_constants as C
import stg_graph as G
from stg_scenario import make_bay, max_height

BANDS_FILE = Path(__file__).resolve().parent / "stg_bands.json"


@dataclass(frozen=True)
class Settings:
    stacks: int = C.DEFAULT_STACKS
    layers: int = C.DEFAULT_LAYERS
    extra: int = C.DEFAULT_EXTRA
    seed: int = C.EVERYDAY_SEED


@dataclass(frozen=True)
class Analysis:
    bay: tuple
    height: int
    containers: int
    lower: int                      # Untergrenze: blockierende Container (Stück 2)
    compact_size: tuple             # (Variablen, Zeilen) des kompakten Modells aus Stück 7
    search: A.SearchResult
    search_ms: float
    graph: tuple | None             # (Knoten, Kanten) der Stapelgraphen; None, wenn mehr als LIVE_MAX_ARCS Kanten
    compact_lp: float | None        # LP-Wert des kompakten Modells (Stück 7), nur wenn die Stapelgraphen gebaut wurden
    cg: G.CGResult | None           # Spaltengenerierung am Wurzelknoten
    flow: G.FlowResult | None       # ganzzahliger Pfadfluss (das bewiesene Optimum der Spaltenformulierung)
    flow_hubs: int | None           # Hübe der aus dem Pfadfluss zusammengesetzten und nachgespielten Hubfolge
    stack_sizes: tuple | None = None   # (Knoten, Kanten) je Stapel

    @property
    def optimum(self):
        """Das Optimum, sobald ein Verfahren es bewiesen hat (Suche oder ganzzahliger Pfadfluss); sonst None."""
        found = {r for r in (self.search.optimum, None if self.flow is None or self.flow.status != "optimal" else round(self.flow.value)) if r is not None}
        assert len(found) <= 1, found
        return found.pop() if found else None

    @property
    def proven(self) -> bool | None:
        """Beweist der Wurzelknoten das Optimum? None, wenn die Spaltenformulierung nicht gerechnet wurde."""
        return None if self.cg is None else G.proven_at_root(self.cg)

    @property
    def stronger(self) -> bool | None:
        """Ist das Spalten-LP strikt stärker als das kompakte LP? None, wenn nicht gerechnet."""
        return None if self.cg is None or self.compact_lp is None else self.cg.value > self.compact_lp + 1e-6


def analyse(settings: Settings, max_arcs: int = C.LIVE_MAX_ARCS) -> Analysis:
    bay = make_bay(settings.stacks, settings.layers, settings.seed)
    height = max_height(settings.layers, settings.extra)
    n = settings.stacks * settings.layers
    csize = M.model_size(settings.stacks, height, n)
    t0 = time.perf_counter()
    search = A.search(bay, height, C.SEARCH_CAP)
    ms = (time.perf_counter() - t0) * 1000
    lower = A.blocker_count(bay)
    try:
        cp = G.build_coupled(bay, height, max_arcs)
    except G.ArcLimit:
        return Analysis(bay, height, n, lower, csize, search, ms, None, None, None, None, None, None)
    compact, _ = M.lp_value(M.build(bay, height))
    cg = G.column_generation(bay, cp)
    flow = G.solve_flow(cp, True, C.FLOW_LIMIT)
    hubs = A.replay(bay, height, G.paths_to_moves(cp, flow.paths)) if flow.paths is not None else None
    return Analysis(bay, height, n, lower, csize, search, ms, (cp.nodes, cp.arcs), compact, cg, flow, hubs, tuple(cp.stack_sizes()))


def num(n: int) -> str:
    """Ganze Zahl mit Leerzeichen als Tausendertrenner."""
    return f"{n:,}".replace(",", " ")


def num_f(x: float) -> str:
    """Zahl mit Leerzeichen als Tausendertrenner; hat sie einen Nachkommaanteil (Median einer geraden Zahl von Läufen), mit einer Nachkommastelle und Komma."""
    x = round(float(x), 6)                                           # 0,9999999999999987 (Rundungsrauschen eines Lösers) ist 1
    if x.is_integer():
        return num(int(x))
    whole, frac = f"{x:.1f}".split(".")
    return f"{num(int(whole))},{frac}"


def lp_text(x: float) -> str:
    """LP-Wert mit höchstens zwei Nachkommastellen (Komma), ganzzahlige Werte ohne."""
    x = round(float(x), 6)
    return num(int(x)) if x.is_integer() else f"{x:.2f}".replace(".", ",")


def sec_text(s: float) -> str:
    """Sekunden: unter 10 mit zwei, sonst mit einer Nachkommastelle (Komma)."""
    return (f"{s:.2f}" if s < 10 else f"{s:.1f}").replace(".", ",")


def time_text(s: float) -> str:
    """Zeit mit Einheit: unter 0,01 s in Millisekunden (sonst stünde „0,00 s“ da), sonst in Sekunden."""
    return f"{ms_text(s * 1000)} ms" if s < 0.01 else f"{sec_text(s)} s"


def ms_text(ms: float) -> str:
    """Millisekunden: unter 10 mit einer Nachkommastelle, sonst ganzzahlig (Komma)."""
    return f"{ms:.1f}".replace(".", ",") if ms < 10 else num(round(ms))


def iter_text(x: float) -> str:
    """„1 Iteration“, sonst „n Iterationen“ (Median kann halbzahlig sein)."""
    return "1 Iteration" if x == 1 else f"{num_f(x)} Iterationen"


def percent_text(x: float) -> str:
    """Anteil als Prozent: unter 10 % mit einer Nachkommastelle, sonst ganzzahlig (Komma)."""
    p = x * 100
    return (f"{p:.1f}" if p < 10 else f"{p:.0f}").replace(".", ",") + " %"


# ---------------------------------------------------------------- Verdikt einer Bucht

def verdict_bay(a: Analysis, max_arcs: int = C.LIVE_MAX_ARCS) -> tuple[str, str]:
    """Verdikt der Kernfrage: ist die Spaltenformulierung stärker, und beweist schon der Wurzelknoten das Optimum?"""
    s = a.search
    if a.cg is None:
        return "info", (f"Die Stapelgraphen hätten mehr als {num(max_arcs)} Kanten (das kompakte Modell hat {num(a.compact_size[0])} Variablen): "
                        f"Die Spaltenformulierung wird hier nicht gerechnet. Die Suche löst die Bucht mit {num(s.nodes)} Knoten in {ms_text(a.search_ms)} ms (Optimum {s.optimum}, Untergrenze {a.lower}).")
    cg = a.cg
    rel = "strikt stärker als" if a.stronger else "gleich dem"
    base = (f"Spalten-LP {lp_text(cg.value)} ({rel} kompakten LP {lp_text(a.compact_lp)}), Lösung aus den erzeugten Spalten {cg.pool_value}, Optimum {a.optimum}; "
            f"{num(cg.columns)} Spalten von {num(cg.arcs)} Kanten in {iter_text(cg.iterations)}.")
    if G.proven_at_root(cg):
        return "success", "Der Wurzelknoten beweist das Optimum: " + base
    return "warning", "Der Wurzelknoten beweist das Optimum nicht (Branch and Price müsste verzweigen): " + base


def result_rows(a: Analysis) -> list[dict]:
    """Zeilen der Ergebnistabelle: Verfahren, Wert, Aufwand."""
    s = a.search
    rows = [{"name": "Suche (IDA* mit Untergrenze und Merken)", "value": "nicht bewiesen" if s.capped else str(s.optimum), "effort": f"{num(s.nodes)} Knoten, {ms_text(a.search_ms)} ms"},
            {"name": "Untergrenze (Stück 2)", "value": str(a.lower), "effort": "Zahl der Blocker"}]
    if a.cg is None:
        rows.append({"name": "Spaltenformulierung", "value": "nicht gerechnet", "effort": f"Stapelgraphen über {num(C.LIVE_MAX_ARCS)} Kanten; kompaktes Modell {num(a.compact_size[0])} Variablen"})
        return rows
    cg, fl = a.cg, a.flow
    rows.insert(1, {"name": "Kompaktes LP (Stück 7)", "value": lp_text(a.compact_lp), "effort": f"{num(a.compact_size[0])} Variablen, {num(a.compact_size[1])} Zeilen"})
    rows.append({"name": "Spalten-LP (Wurzelknoten)", "value": lp_text(cg.value), "effort": f"{iter_text(cg.iterations)}, {num(cg.columns)} Spalten von {num(cg.arcs)} Kanten, {sec_text(cg.seconds)} s"})
    rows.append({"name": "Lösung aus den erzeugten Spalten (Preis und Verzweige)", "value": "–" if cg.pool_value is None else str(cg.pool_value), "effort": "obere Schranke, nicht notwendig das Optimum"})
    rows.append({"name": "Ganzzahliger Pfadfluss (alle Spalten)", "value": "kein Beweis" if fl.status != "optimal" else str(round(fl.value)),
                 "effort": f"{num(fl.nodes)} Knoten, {num(fl.arcs)} Kanten, {sec_text(fl.seconds_solve)} s"})
    return rows


def path_rows(cp: G.Coupled, paths) -> list[dict]:
    """Die Pfade der Stapel als Tabellenzeilen: je Stapel und Periode der Inhalt zu Beginn, die Zugänge und die Abgänge (Stapel von 1, Container von unten nach oben)."""
    rows = []
    for s, path in enumerate(paths):
        g = cp.graphs[s]
        for a in path:
            u, v, cost, t, arr, dep = g.arcs[a]
            rows.append({"stack": s + 1, "period": t, "content": "(" + ", ".join(str(c) for c in g.content(u)) + ")" if g.content(u) else "()",
                         "arrivals": ", ".join(str(c) for c in arr) or "–", "departures": ", ".join(str(c) for c in dep) or "–"})
    return rows


# ---------------------------------------------------------------- Stichproben (vorberechnet)

def _stat(xs):
    xs = list(xs)
    if not xs:
        return {"n": 0, "median": None, "mean": None, "min": None, "max": None}
    return {"n": len(xs), "median": median(xs), "mean": mean(xs), "min": min(xs), "max": max(xs)}


def cell_rows(stacks: int, layers: int, extra: int, seeds, use_cg: bool = True) -> list[dict]:
    """Eine Zeile je feste Bucht: Optimum (Suche), Untergrenze, kompaktes LP, Spalten-LP (mit Spaltengenerierung oder, bei `use_cg=False`, als voller Pfadfluss), Größe der Stapelgraphen
    und bei Spaltengenerierung Iterationen, Spalten, Wurzel ganzzahlig, Wert der Pool-Lösung und Zeiten. Langsam bei großen Zellen, nur offline und in Tests."""
    height = max_height(layers, extra)
    rows = []
    for sd in seeds:
        bay = make_bay(stacks, layers, sd)
        opt = A.search(bay, height, C.SEARCH_CAP).optimum
        compact, _ = M.lp_value(M.build(bay, height))
        t0 = time.perf_counter()
        cp = G.build_coupled(bay, height)
        build_s = time.perf_counter() - t0
        row = {"seed": sd, "lb": A.blocker_count(bay), "opt": opt, "compact": compact, "arcs": cp.arcs, "nodes": cp.nodes, "build_s": build_s, "iterations": None, "columns": None,
               "integral": None, "pool": None, "proven": None, "cg_s": None, "price_s": None, "flow_s": None}
        if use_cg:
            cg = G.column_generation(bay, cp)
            row.update(value=cg.value, iterations=cg.iterations, columns=cg.columns, integral=cg.integral, pool=cg.pool_value, proven=G.proven_at_root(cg), cg_s=cg.seconds, price_s=cg.price_seconds)
        else:
            fl = G.solve_flow(cp, False, 300)
            row.update(value=fl.value, flow_s=fl.seconds_solve)
        rows.append(row)
    return rows


def cell_stats(rows: list[dict], stacks: int, layers: int, extra: int = C.DEFAULT_EXTRA) -> dict:
    """Kennzahlen einer Stichprobe: Größe der Stapelgraphen (Kanten, Knoten, Aufbauzeit) gegen die Variablen des kompakten Modells; Stärke der Schranke (Spalten-LP und kompaktes LP
    gegen das Optimum, Zahl der Buchten mit strikt stärkerem und schwächerem Spalten-LP, Lücken); bei Spaltengenerierung Iterationen, Spalten, Anteil des Preisproblems,
    ganzzahlige Wurzeln, Pool-Lösungen gleich dem Optimum, im Wurzelknoten bewiesene Buchten und die Liste der unbewiesenen."""
    eps = 1e-6
    n = len(rows)
    cg = [r for r in rows if r["iterations"] is not None]
    out = {"n": n, "containers": stacks * layers, "compact_vars": M.model_size(stacks, max_height(layers, extra), stacks * layers)[0],
           "arcs": _stat(r["arcs"] for r in rows), "nodes": _stat(r["nodes"] for r in rows), "build_s": _stat(r["build_s"] for r in rows),
           "cols_equal": sum(abs(r["value"] - r["opt"]) < eps for r in rows), "compact_equal": sum(abs(r["compact"] - r["opt"]) < eps for r in rows),
           "stronger": sum(r["value"] > r["compact"] + eps for r in rows), "weaker": sum(r["value"] < r["compact"] - eps for r in rows),
           "gap_cols": {"median": median(r["opt"] - r["value"] for r in rows), "max": max(r["opt"] - r["value"] for r in rows)},
           "gap_compact": {"median": median(r["opt"] - r["compact"] for r in rows), "max": max(r["opt"] - r["compact"] for r in rows)}}
    if cg:
        out["cg"] = {"n": len(cg), "iterations": _stat(r["iterations"] for r in cg), "columns": _stat(r["columns"] for r in cg),
                     "share": median(r["columns"] / r["arcs"] for r in cg), "seconds": _stat(r["cg_s"] for r in cg),
                     "price_share": sum(r["price_s"] for r in cg) / sum(r["cg_s"] for r in cg), "integral": sum(bool(r["integral"]) for r in cg),
                     "pool_equal": sum(r["pool"] == r["opt"] for r in cg), "proven": sum(bool(r["proven"]) for r in cg),
                     "proven_compact": sum(math.ceil(r["compact"] - eps) == r["pool"] for r in cg),
                     "unproven": [{"seed": r["seed"], "opt": r["opt"], "value": round(r["value"], 3), "pool": r["pool"]} for r in cg if not r["proven"]]}
    else:
        out["flow"] = {"seconds": _stat(r["flow_s"] for r in rows)}
    return out


def fix_rows(stacks: int, layers: int, extra: int, seeds, time_limit: float = 60.0) -> list[dict]:
    """Eine Zeile je feste Bucht: der Master ohne die Ordnungsbedingung (O), ganzzahlig: kleiner als das Optimum, und ob die zusammengesetzte Hubfolge spielbar ist."""
    height = max_height(layers, extra)
    rows = []
    for sd in seeds:
        bay = make_bay(stacks, layers, sd)
        opt = A.search(bay, height, C.SEARCH_CAP).optimum
        cp = G.build_coupled(bay, height, order=False)
        r = G.solve_flow(cp, True, time_limit)
        smaller, playable = None, None
        if r.paths is not None:
            smaller = round(r.value) < opt
            try:
                A.replay(bay, height, G.paths_to_moves(cp, r.paths))
                playable = True
            except ValueError:
                playable = False
        rows.append({"seed": sd, "opt": opt, "value": None if r.value is None else round(r.value), "smaller": smaller, "playable": playable})
    return rows


def fix_stats(rows: list[dict]) -> dict:
    solved = [r for r in rows if r["smaller"] is not None]
    return {"n": len(rows), "solved": len(solved), "smaller": sum(r["smaller"] for r in solved), "unplayable": sum(not r["playable"] for r in solved),
            "wrong": sum(r["smaller"] or not r["playable"] for r in solved)}


def load_bands() -> dict:
    """Vorberechnete Kennzahlen, erzeugt von generate_precomputed.py: {"zellen": {"s,l": cell_stats}, "korrektur": {"s,l": fix_stats}}."""
    return json.loads(BANDS_FILE.read_text(encoding="utf-8"))


def cell_key(stacks: int, layers: int) -> str:
    return f"{stacks},{layers}"


# ---------------------------------------------------------------- Verdikte der Tabellen

def verdict_size(stats: dict, name: str) -> tuple[str, str]:
    """Verdikt „wie groß wird der Stapelgraph?“: Kanten gegen die Variablen des kompakten Modells."""
    a = stats["arcs"]
    ratio = a["median"] / stats["compact_vars"]
    ratio_txt = f"{ratio:.2f}".replace(".", ",")
    text = (f"{name} ({stats['containers']} Container): Die Stapelgraphen haben im Median {num_f(a['median'])} Kanten (Maximum {num(a['max'])}), das kompakte Modell {num(stats['compact_vars'])} Variablen "
            f"(Verhältnis {ratio_txt}).")
    if ratio <= C.SMALL_GRAPH_RATIO:
        return "info", text + " Der Stapelgraph ist hier kleiner als das kompakte Modell."
    return "warning", text + " Der Stapelgraph ist hier größer als das kompakte Modell."


def verdict_strength(stats: dict, name: str) -> tuple[str, str]:
    """Verdikt „wie stark ist die Schranke?“: Buchten mit strikt stärkerem Spalten-LP, nie schwächer, Lücken."""
    n = stats["n"]
    text = (f"{name}: Das Spalten-LP trifft das Optimum in {stats['cols_equal']} von {n} Buchten, das kompakte in {stats['compact_equal']}; strikt stärker in {stats['stronger']}, schwächer in {stats['weaker']}; "
            f"Optimum minus LP-Wert im Median {num_f(stats['gap_cols']['median'])} (Maximum {lp_text(stats['gap_cols']['max'])}) gegen {num_f(stats['gap_compact']['median'])} (Maximum {lp_text(stats['gap_compact']['max'])}).")
    if stats["weaker"]:
        return "warning", text + " Das Spalten-LP war in einer Bucht schwächer: Das darf nicht sein."
    if stats["stronger"] / n >= C.STRONG_SHARE:
        return "success", text + " Die Spaltenformulierung ist hier meist stärker."
    if stats["stronger"]:
        return "info", text + " Die Spaltenformulierung ist hier in einem Teil der Buchten stärker."
    return "info", text + " Beide Schranken sind hier gleich gut."


def verdict_columns(stats: dict, name: str) -> tuple[str, str]:
    """Verdikt „wie viele Spalten braucht die Generierung?“: Spalten gegen Kanten, Anteil des Preisproblems, im Wurzelknoten bewiesene Buchten."""
    c = stats["cg"]
    text = (f"{name}: {num_f(c['columns']['median'])} Spalten im Median (Maximum {num(c['columns']['max'])}) von {num_f(stats['arcs']['median'])} Kanten in {iter_text(c['iterations']['median'])}; "
            f"das Preisproblem braucht {percent_text(c['price_share'])} der Zeit; der Wurzelknoten beweist das Optimum in {c['proven']} von {c['n']} Buchten "
            f"(mit dem kompakten LP: {c['proven_compact']}), die Wurzel ist in {c['integral']} ganzzahlig.")
    if c["proven"] < c["n"]:
        return "warning", text + f" In {c['n'] - c['proven']} Buchten müsste Branch and Price verzweigen."
    return "info", text + " In dieser Stichprobe wäre Verzweigen nicht nötig."


def verdict_fix(stats: dict, name: str) -> tuple[str, str]:
    """Verdikt „braucht der Master die Ordnungsbedingung (O)?“: Buchten, in denen der Master ohne (O) ein zu kleines Optimum liefert oder eine nicht spielbare Lösung."""
    text = (f"{name}: Ohne die Ordnungsbedingung (O) liefert der ganzzahlige Master in {stats['smaller']} von {stats['solved']} Buchten ein zu kleines Optimum und in {stats['unplayable']} eine "
            f"Lösung, die sich nicht als Hubfolge nachspielen lässt; mit (O) stimmen alle.")
    if stats["wrong"]:
        return "warning", text
    return "info", f"{name}: Hier macht die Ordnungsbedingung (O) keinen Unterschied: In allen {stats['solved']} Buchten stimmt auch der Master ohne sie."
