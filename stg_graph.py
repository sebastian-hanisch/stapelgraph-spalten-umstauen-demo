"""Spaltenformulierung (Dantzig-Wolfe der Stapel) des restricted Umstauens: Stapelgraph, Pfadfluss, Spaltengenerierung.

Eine **Spalte** gehört zu einem Stapel und beschreibt seinen **Inhalt zu Beginn jeder Periode** t = 1..N (Periode t = Abruf des Containers t, wie im kompakten Modell):
  liegt t im Stapel: alle Container über t gehen ab (Abgänge, oben zuerst), t wird abgerufen; neuer Inhalt = der Teil unter t
  sonst: Zugänge = eine geordnete Liste verschiedener Container n > t, die nicht im Stapel liegen, soweit Platz ist (Höchsthöhe H); neuer Inhalt = alter Inhalt + Zugänge
Kosten einer Spalte: Zahl der Zugänge. Die Spalten eines Stapels sind die **Pfade im Stapelgraphen** (Knoten = (t, Inhalt), Kanten = Perioden-Schritte).
Master (Kopplung der Stapel):
  (P) Pfad     je Stapel genau ein Pfad (Fluss 1 von der Quelle zur Senke)
  (B) Bilanz   je Container n und Periode t: Zugänge von n in t = Abgänge von n in t, summiert über alle Stapel
  (O) Ordnung  je Periode t und Paar (b1, b2): kommen beide im selben Stapel an, und b1 ging vor b2 ab (b1 lag über b2), dann kommt b1 vor b2 an:
               Summe der Kanten mit Ankunft b2 vor b1 <= 1 - Summe der Kanten mit Abgang b1 vor b2   (`order=False` lässt (O) weg: die Gegenprobe)
Der Master ist exakt (ganzzahlig = das Optimum). Der **Pfadfluss** (eine Variable je Kante) ist dieselbe LP wie der Master mit allen Spalten; die **Spaltengenerierung** löst
sie mit wenigen Spalten (Preisproblem: kürzester Pfad im Stapelgraphen mit den Dualwerten). Eigene Konstruktion in der Idee der Spaltenformulierungen für Stapelprobleme
(van Brink und van der Zwaan, arXiv 1406.7107, für das Premarshalling); das Modell von Zehendner und Feillet für das Umstauen ist hier nicht nachgebaut.
"""

import itertools
import math
import time
from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix

from stg_algorithm import child_targets


class ArcLimit(Exception):
    """Der Stapelgraph hat mehr Kanten als erlaubt (Abbruch beim Bau)."""


class StackGraph:
    """Der Stapelgraph eines Stapels: Knoten (t, Inhalt), Kanten (von, nach, Kosten, t, Ankünfte, Abgänge)."""

    def __init__(self, content, n_all, height, budget=None):
        self.n_all, self.height = n_all, height
        self.nodes = {}
        self.arcs = []
        start = (1, tuple(content))
        self._build(start, budget)
        self.source = self.nodes[start]
        self.sink = self.nodes[(n_all + 1, ())]
        self.inv = {v: k for k, v in self.nodes.items()}

    def _node(self, key):
        if key not in self.nodes:
            self.nodes[key] = len(self.nodes)
        return self.nodes[key]

    def _build(self, start, budget):
        seen = {start}
        todo = [start]
        while todo:
            t, cont = todo.pop()
            u = self._node((t, cont))
            if t > self.n_all:
                continue
            nxt = []
            if t in cont:
                pos = cont.index(t)
                nxt.append(((t + 1, cont[:pos]), 0, (), tuple(reversed(cont[pos + 1:]))))
            else:
                pool = [n for n in range(t + 1, self.n_all + 1) if n not in cont]
                for k in range(0, min(self.height - len(cont), len(pool)) + 1):
                    for arr in itertools.permutations(pool, k):
                        nxt.append(((t + 1, cont + arr), k, arr, ()))
            if budget is not None:
                budget[0] -= len(nxt)
                if budget[0] < 0:
                    raise ArcLimit
            for key, cost, arr, dep in nxt:
                v = self._node(key)
                self.arcs.append((u, v, cost, t, arr, dep))
                if key not in seen:
                    seen.add(key)
                    todo.append(key)

    def content(self, node):
        return self.inv[node][1]

    def period(self, node):
        return self.inv[node][0]


@dataclass
class Coupled:
    """Die Stapelgraphen einer Bucht mit den Kopplungszeilen (B) und (O)."""
    graphs: list
    n: int
    height: int
    bal: dict           # (n, t) -> [(Stapel, Kante, Koeffizient)]
    order: dict         # (t, b1, b2) -> ([(Stapel, Kante)] Ankunft b2 vor b1, [(Stapel, Kante)] Abgang b1 vor b2)
    use_order: bool

    @property
    def arcs(self) -> int:
        return sum(len(g.arcs) for g in self.graphs)

    @property
    def nodes(self) -> int:
        return sum(len(g.nodes) for g in self.graphs)

    def stack_sizes(self) -> list:
        """[(Knoten, Kanten)] je Stapel."""
        return [(len(g.nodes), len(g.arcs)) for g in self.graphs]


def build_coupled(bay, height, max_arcs=None, order=True) -> Coupled:
    """Baut die Stapelgraphen und die Kopplungszeilen. Wirft ArcLimit, wenn zusammen mehr als `max_arcs` Kanten nötig wären (der Bau bricht dann sofort ab)."""
    n = sum(len(s) for s in bay)
    if sorted(c for s in bay for c in s) != list(range(1, n + 1)):
        raise ValueError("die Abrufnummern müssen 1 bis N sein")
    if any(len(s) > height for s in bay):
        raise ValueError("ein Stapel ist höher als die Höchsthöhe")
    budget = None if max_arcs is None else [max_arcs]
    graphs = [StackGraph(s, n, height, budget) for s in bay]
    bal, ordr = {}, {}
    for s, g in enumerate(graphs):
        for a, (u, v, cost, t, arr, dep) in enumerate(g.arcs):
            for x in arr:
                bal.setdefault((x, t), []).append((s, a, 1.0))
            for x in dep:
                bal.setdefault((x, t), []).append((s, a, -1.0))
            if order:
                for i in range(len(arr)):
                    for j in range(i + 1, len(arr)):
                        ordr.setdefault((t, arr[j], arr[i]), ([], []))[0].append((s, a))     # arr[i] kommt vor arr[j]: das Paar (b1 = arr[j], b2 = arr[i]) wird verletzt
                for i in range(len(dep)):
                    for j in range(i + 1, len(dep)):
                        ordr.setdefault((t, dep[i], dep[j]), ([], []))[1].append((s, a))     # dep[i] ging vor dep[j] ab: b1 = dep[i], b2 = dep[j]
    ordr = {k: v for k, v in ordr.items() if v[0] and v[1]}
    return Coupled(graphs, n, height, bal, ordr, order)


# ---------------------------------------------------------------- Pfadfluss (alle Spalten)

@dataclass(frozen=True)
class FlowResult:
    value: float | None         # Zielwert (LP-Wert oder ganzzahliges Optimum), None ohne Lösung
    status: str                 # "optimal", "time_limit", "infeasible", "error"
    seconds_build: float
    seconds_solve: float
    arcs: int
    nodes: int
    rows: int
    paths: tuple | None         # bei ganzzahliger Lösung: je Stapel die Liste der Kantenindizes (Periode 1 bis N)


def flow_matrices(cp: Coupled):
    """(c, A_eq, b_eq, A_ub, b_ub, Offsets): Pfadfluss mit Kopplung."""
    graphs = cp.graphs
    offsets = np.cumsum([0] + [len(g.arcs) for g in graphs])
    nv = int(offsets[-1])
    c = np.zeros(nv)
    eq_r, eq_c, eq_v, beq = [], [], [], []
    r = 0
    for s, g in enumerate(graphs):
        inc = [[] for _ in g.nodes]
        outg = [[] for _ in g.nodes]
        for a, (u, v, cost, t, arr, dep) in enumerate(g.arcs):
            c[offsets[s] + a] = cost
            outg[u].append(a)
            inc[v].append(a)
        for node in range(len(g.nodes)):
            for a in outg[node]:
                eq_r.append(r); eq_c.append(offsets[s] + a); eq_v.append(1.0)
            for a in inc[node]:
                eq_r.append(r); eq_c.append(offsets[s] + a); eq_v.append(-1.0)
            beq.append(1.0 if node == g.source else (-1.0 if node == g.sink else 0.0))
            r += 1
    for ents in cp.bal.values():
        for s, a, cf in ents:
            eq_r.append(r); eq_c.append(offsets[s] + a); eq_v.append(cf)
        beq.append(0.0)
        r += 1
    ub_r, ub_c, ub_v = [], [], []
    r2 = 0
    for viol, dep in cp.order.values():
        for s, a in viol:
            ub_r.append(r2); ub_c.append(offsets[s] + a); ub_v.append(1.0)
        for s, a in dep:
            ub_r.append(r2); ub_c.append(offsets[s] + a); ub_v.append(1.0)
        r2 += 1
    a_eq = coo_matrix((eq_v, (eq_r, eq_c)), shape=(r, nv)).tocsr()
    a_ub = coo_matrix((ub_v, (ub_r, ub_c)), shape=(r2, nv)).tocsr() if r2 else None
    return c, a_eq, np.array(beq), a_ub, np.ones(r2), offsets


def extract_paths(cp: Coupled, offsets, x) -> tuple:
    """Pfade (je Stapel Kantenindizes von Periode 1 bis N) aus einer ganzzahligen Pfadfluss-Lösung."""
    paths = []
    for s, g in enumerate(cp.graphs):
        out = {}
        for a, (u, v, cost, t, arr, dep) in enumerate(g.arcs):
            if x[offsets[s] + a] > 0.5:
                out[u] = a
        path, node = [], g.source
        while node != g.sink:
            a = out[node]
            path.append(a)
            node = g.arcs[a][1]
        paths.append(path)
    return tuple(paths)


def solve_flow(cp: Coupled, integral: bool = False, time_limit: float = 120.0, build_seconds: float = 0.0) -> FlowResult:
    """Löst den Pfadfluss: integral=False die LP-Relaxation (Schranke der Spaltenformulierung), True ganzzahlig (das Optimum, bewiesen bei Status "optimal")."""
    t0 = time.perf_counter()
    c, a_eq, b_eq, a_ub, b_ub, offsets = flow_matrices(cp)
    cons = [LinearConstraint(a_eq, b_eq, b_eq)]
    if a_ub is not None:
        cons.append(LinearConstraint(a_ub, -np.inf, b_ub))
    t1 = time.perf_counter()
    res = milp(c, constraints=cons, integrality=np.ones_like(c) if integral else np.zeros_like(c), bounds=Bounds(0, 1), options={"time_limit": float(time_limit), "disp": False})
    t2 = time.perf_counter()
    status = {0: "optimal", 1: "time_limit", 2: "infeasible"}.get(res.status, "error")
    value = float(res.fun) if res.status == 0 else None
    paths = extract_paths(cp, offsets, res.x) if (integral and res.status == 0) else None
    return FlowResult(value, status, build_seconds + (t1 - t0), t2 - t1, cp.arcs, cp.nodes, a_eq.shape[0] + (0 if a_ub is None else a_ub.shape[0]), paths)


# ---------------------------------------------------------------- Pfade und Hubfolgen

def paths_to_moves(cp: Coupled, paths) -> list:
    """Setzt die Pfade der Stapel zu einer Hubfolge [(Periode, Container, Zielstapel)] zusammen: je Periode die Abgänge des Zielstapels von oben nach unten, das Ziel ist der
    Stapel, in dem der Container ankommt. Wirft ValueError, wenn ein Abgang nirgends ankommt."""
    moves = []
    for t in range(1, cp.n + 1):
        arcs = [cp.graphs[s].arcs[paths[s][t - 1]] for s in range(len(cp.graphs))]
        for a in arcs:
            for b in a[5]:
                dest = [k for k, o in enumerate(arcs) if b in o[4]]
                if len(dest) != 1:
                    raise ValueError(f"Periode {t}: Container {b} kommt nicht in genau einem Stapel an")
                moves.append((t, b, dest[0]))
    return moves


def heuristic_hubs(bay, height):
    """Regel der engsten Passung (Stück 1) als Hubfolge [(Container, Zielstapel)]: eine zulässige Startlösung."""
    st = [list(s) for s in bay]
    hubs = []
    for t in range(1, sum(len(s) for s in st) + 1):
        src = next(i for i, s in enumerate(st) if t in s)
        while st[src][-1] != t:
            c = st[src][-1]
            base = [list(s) for s in st]
            base[src].pop()
            k = child_targets(tuple(tuple(s) for s in base), src, height, c)[0]
            st[src].pop()
            st[k].append(c)
            hubs.append((c, k))
        st[src].pop()
    return hubs


def paths_from_hubs(bay, cp: Coupled, hubs) -> list:
    """Übersetzt eine Hubfolge [(Container, Zielstapel)] in je einen Pfad (Kantenindizes) je Stapelgraph."""
    n = cp.n
    st = [list(s) for s in bay]
    todo = list(hubs)
    arrivals, departures, snap = {}, {}, {}
    for t in range(1, n + 1):
        for s in range(len(st)):
            snap[(s, t)] = tuple(st[s])
        src = next(i for i, s in enumerate(st) if t in s)
        while st[src][-1] != t:
            c, k = todo.pop(0)
            if st[src][-1] != c:
                raise ValueError("die Hubfolge bewegt nicht den obersten Container")
            departures.setdefault((src, t), []).append(c)
            arrivals.setdefault((k, t), []).append(c)
            st[k].append(st[src].pop())
        st[src].pop()
    paths = []
    for s, g in enumerate(cp.graphs):
        index = {(g.content(u), t, arr, dep): a for a, (u, v, cost, t, arr, dep) in enumerate(g.arcs)}
        paths.append([index[(snap[(s, t)], t, tuple(arrivals.get((s, t), [])), tuple(departures.get((s, t), [])))] for t in range(1, n + 1)])
    return paths


# ---------------------------------------------------------------- Spaltengenerierung

@dataclass(frozen=True)
class CGResult:
    value: float                # LP-Wert der Spaltenformulierung (Wurzelknoten)
    iterations: int
    columns: int                # Zahl der erzeugten Spalten (inklusive Startspalten)
    arcs: int
    nodes: int
    seconds: float              # Spaltengenerierung (ohne Bau der Graphen)
    price_seconds: float        # davon das Preisproblem
    integral: bool              # Wurzellösung ganzzahlig?
    pool_value: int | None      # Preis und Verzweige: der Master mit den erzeugten Spalten ganzzahlig gelöst (obere Schranke, nicht notwendig das Optimum)
    solution: tuple             # die Wurzellösung: je Spalte (Stapel, Gewicht, Pfad) mit Gewicht > 0


def column_generation(bay, cp: Coupled, max_iter: int = 1000, tol: float = 1e-9) -> CGResult:
    """Spaltengenerierung am Wurzelknoten (Startlösung: Regel der engsten Passung). Zum Schluss der Master mit den erzeugten Spalten ganzzahlig (Preis und Verzweige)."""
    t0 = time.perf_counter()
    graphs, n = cp.graphs, cp.n
    bal_keys = list(cp.bal)
    bal_row = {k: i for i, k in enumerate(bal_keys)}
    ord_keys = list(cp.order)
    ord_row = {k: i for i, k in enumerate(ord_keys)}
    arc_bal = [dict() for _ in graphs]
    arc_ord = [dict() for _ in graphs]
    for k, ents in cp.bal.items():
        for s, a, cf in ents:
            d = arc_bal[s].setdefault(a, {})
            d[bal_row[k]] = d.get(bal_row[k], 0.0) + cf
    for k in ord_keys:
        viol, dep = cp.order[k]
        for s, a in viol:
            arc_ord[s].setdefault(a, {})[ord_row[k]] = 1.0
        for s, a in dep:
            arc_ord[s].setdefault(a, {})[ord_row[k]] = 1.0
    nb, no, ns = len(bal_keys), len(ord_keys), len(graphs)
    by_node, topo = [], []
    for g in graphs:
        bn = {}
        for a, arc in enumerate(g.arcs):
            bn.setdefault(arc[0], []).append(a)
        by_node.append(bn)
        topo.append(sorted(range(len(g.nodes)), key=g.period))
    columns, seen = [], set()

    def add_path(s, path):
        key = (s, tuple(path))
        if key in seen:
            return False
        seen.add(key)
        columns.append((s, list(path)))
        return True

    for s, path in enumerate(paths_from_hubs(bay, cp, heuristic_hubs(bay, cp.height))):
        add_path(s, path)

    def vectors(s, path):
        cost = sum(graphs[s].arcs[a][2] for a in path)
        b, o = {}, {}
        for a in path:
            for r, cf in arc_bal[s].get(a, {}).items():
                b[r] = b.get(r, 0.0) + cf
            for r, cf in arc_ord[s].get(a, {}).items():
                o[r] = o.get(r, 0.0) + cf
        return cost, b, o

    def master(integral):
        c = np.zeros(len(columns))
        eq_r, eq_c, eq_v, ub_r, ub_c, ub_v = [], [], [], [], [], []
        for j, (s, p) in enumerate(columns):
            cost, b, o = vectors(s, p)
            c[j] = cost
            for r, cf in b.items():
                eq_r.append(r); eq_c.append(j); eq_v.append(cf)
            eq_r.append(nb + s); eq_c.append(j); eq_v.append(1.0)
            for r, cf in o.items():
                ub_r.append(r); ub_c.append(j); ub_v.append(cf)
        a_eq = coo_matrix((eq_v, (eq_r, eq_c)), shape=(nb + ns, len(columns))).tocsr()
        b_eq = np.concatenate([np.zeros(nb), np.ones(ns)])
        a_ub = coo_matrix((ub_v, (ub_r, ub_c)), shape=(no, len(columns))).tocsr() if no else None
        if integral:
            cons = [LinearConstraint(a_eq, b_eq, b_eq)]
            if a_ub is not None:
                cons.append(LinearConstraint(a_ub, -np.inf, np.ones(no)))
            return milp(c, constraints=cons, integrality=np.ones_like(c), bounds=Bounds(0, 1), options={"time_limit": 60.0, "disp": False})
        return linprog(c, A_ub=a_ub, b_ub=np.ones(no) if no else None, A_eq=a_eq, b_eq=b_eq, bounds=(0, None), method="highs")

    it, t_price = 0, 0.0
    while True:
        it += 1
        res = master(False)
        if res.status != 0:
            raise RuntimeError(res.message)
        y_eq = res.eqlin.marginals
        y_ub = res.ineqlin.marginals if no else np.zeros(0)
        added = 0
        tp = time.perf_counter()
        for s, g in enumerate(graphs):
            dist, pred = {g.source: 0.0}, {}
            for u in topo[s]:
                if u not in dist:
                    continue
                for a in by_node[s].get(u, []):
                    _, v, cost, t, arr, dep = g.arcs[a]
                    rc = cost - sum(y_eq[r] * cf for r, cf in arc_bal[s].get(a, {}).items()) - sum(y_ub[r] * cf for r, cf in arc_ord[s].get(a, {}).items())
                    d = dist[u] + rc
                    if v not in dist or d < dist[v] - 1e-12:
                        dist[v], pred[v] = d, (u, a)
            if dist.get(g.sink, 0.0) - y_eq[nb + s] < -tol:
                path, v = [], g.sink
                while v != g.source:
                    u, a = pred[v]
                    path.append(a)
                    v = u
                if add_path(s, path[::-1]):
                    added += 1
        t_price += time.perf_counter() - tp
        if added == 0 or it >= max_iter:
            break
    x = res.x
    integral = bool(np.all(np.minimum(np.abs(x), np.abs(1 - x)) < 1e-6))
    solution = tuple((columns[j][0], float(x[j]), tuple(columns[j][1])) for j in range(len(columns)) if x[j] > 1e-9)
    ires = master(True)
    pool = int(round(ires.fun)) if ires.status == 0 else None
    return CGResult(float(res.fun), it, len(columns), cp.arcs, cp.nodes, time.perf_counter() - t0, t_price, integral, pool, solution)


def proven_at_root(cg: CGResult) -> bool:
    """Beweist der Wurzelknoten das Optimum? Ja, wenn der aufgerundete LP-Wert dem Wert der Lösung aus den erzeugten Spalten gleicht (alle Kosten sind ganzzahlig)."""
    return cg.pool_value is not None and math.ceil(cg.value - 1e-6) == cg.pool_value
