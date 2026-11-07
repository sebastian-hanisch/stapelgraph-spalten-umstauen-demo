"""Das kompakte, zeitindizierte Modell aus Stück 7 (verschlankt: nur Größe, Bau und LP-Wert; zum Vergleich der Schranken).

Zeitindiziertes ILP für das restricted Block Relocation Problem (HiGHS über scipy.optimize.milp).

Nachbau des Modells BRP-II in der korrigierten Fassung (BRP2c), wie es Eskandari und Azari (Scientia Iranica 22(6), 2015, S. 2722-2728) wiedergeben (Caserta, Schwarze und Voß,
EJOR 219, 2012, im Volltext nicht gelesen). Eigene Umsetzung mit Variablenreduktion.

  Perioden  t = 1..N: Periode t ist der Abruf des Containers t; die Umlagerungen der Periode geschehen davor.
  b[i,j,n,t]      Container n liegt zu Beginn der Periode t auf Stapel i, Lage j (nur n >= t)
  x[i,j,k,l,n,t]  in Periode t wird n von (i,j) nach (k,l) umgelagert (nur n > t, i != k)
  Zielfunktion    Summe aller x
  (T)  Übergang   b[i,j,n,t+1] = b[i,j,n,t] - sum_kl x[i,j,k,l,n,t] + sum_kl x[k,l,i,j,n,t]
  (E)  Platz      jeder verbleibende Container hat genau einen Platz, je Platz höchstens ein Container, Schwerkraft (Lage j+1 besetzt => Lage j besetzt), Layouts t = 2..N
  (R)  Restricted nur Container über dem Ziel t im Zielstapel werden bewegt: sum x[i,j,...,t] <= sum_{j0<j} b[i,j0,t,t]; ein Container kann nur von seinem Platz weg
  (L)  LIFO       H*sum_n x[i,j,k,l,n,t] + sum_{j'>j} sum_{l'>l} sum_n x[i,j',k,l',n,t] <= H   (Korrektur (9) von Eskandari und Azari; `lifo="original"`: Faktor 1 statt H, die
                  fehlerhafte Fassung (6) von BRP-II)
Der Abruf ist implizit: Was über dem Ziel liegt, muss weg, sonst verletzt das nächste Layout die Schwerkraft.
"""

import time
from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix, csr_matrix


def model_size(stacks: int, height: int, containers: int) -> tuple[int, int]:
    """(Variablen, Zeilen) des Modells aus Stapelzahl W, Höchsthöhe H und Containerzahl N, ohne es zu bauen:
    Variablen = W*H*N*(N+1)/2 + W*(W-1)*H^2*N*(N-1)/2; Zeilen = W*H*N*(N-1) + (N-1)*(2*W*H + W*(W-1)*H^2 + W*(H-1)) + N*(N-1)/2."""
    w, h, n = stacks, height, containers
    variables = w * h * n * (n + 1) // 2 + w * (w - 1) * h * h * n * (n - 1) // 2
    rows = w * h * n * (n - 1) + (n - 1) * (2 * w * h + w * (w - 1) * h * h + w * (h - 1)) + n * (n - 1) // 2
    return variables, rows


@dataclass(frozen=True)
class Model:
    c: np.ndarray
    a: csr_matrix
    lo: np.ndarray
    hi: np.ndarray
    lb: np.ndarray
    ub: np.ndarray
    b_index: dict           # (i, j, n, t) -> Variablenindex
    x_index: dict           # (i, j, k, l, n, t) -> Variablenindex
    stacks: int
    height: int
    containers: int

    @property
    def size(self) -> tuple[int, int, int]:
        """(Variablen, Zeilen, Nichtnullen)."""
        return len(self.c), self.a.shape[0], int(self.a.nnz)


def build(bay, height: int, lifo: str = "corrected") -> Model:
    """Baut das Modell. bay: Tupel von Stapeln (unten nach oben) mit den Nummern 1..N; height: Höchsthöhe."""
    if lifo not in ("corrected", "original"):
        raise ValueError(f"unbekannte LIFO-Fassung {lifo!r}")
    w, h = len(bay), height
    nums = sorted(c for s in bay for c in s)
    n_all = len(nums)
    if nums != list(range(1, n_all + 1)):
        raise ValueError("die Abrufnummern müssen 1 bis N sein")
    if any(len(s) > h for s in bay):
        raise ValueError("ein Stapel ist höher als die Höchsthöhe")
    init = {c: (i, j) for i, s in enumerate(bay) for j, c in enumerate(s)}
    b_index, x_index = {}, {}
    nv = 0
    for t in range(1, n_all + 1):
        for n in range(t, n_all + 1):
            for i in range(w):
                for j in range(h):
                    b_index[(i, j, n, t)] = nv
                    nv += 1
    xs = {}
    for t in range(1, n_all):
        for n in range(t + 1, n_all + 1):
            for i in range(w):
                for j in range(h):
                    for k in range(w):
                        if k == i:
                            continue
                        for l in range(h):
                            x_index[(i, j, k, l, n, t)] = nv
                            xs.setdefault((i, j, k, l, t), []).append(nv)
                            nv += 1
    rows, cols, vals, lo, hi = [], [], [], [], []
    r = [0]

    def add(entries, lo_, hi_):
        for v, cf in entries:
            rows.append(r[0]); cols.append(v); vals.append(cf)
        lo.append(lo_); hi.append(hi_); r[0] += 1

    lbv, ubv = np.zeros(nv), np.ones(nv)
    for n in range(1, n_all + 1):                                       # Anfangslayout fest
        for i in range(w):
            for j in range(h):
                v = b_index[(i, j, n, 1)]
                lbv[v] = ubv[v] = 1.0 if init[n] == (i, j) else 0.0
    factor = float(h) if lifo == "corrected" else 1.0
    rhs = float(h) if lifo == "corrected" else 1.0
    for t in range(1, n_all):
        for n in range(t + 1, n_all + 1):                               # (T)
            for i in range(w):
                for j in range(h):
                    e = [(b_index[(i, j, n, t + 1)], 1.0), (b_index[(i, j, n, t)], -1.0)]
                    for k in range(w):
                        if k == i:
                            continue
                        for l in range(h):
                            e.append((x_index[(i, j, k, l, n, t)], 1.0))
                            e.append((x_index[(k, l, i, j, n, t)], -1.0))
                    add(e, 0.0, 0.0)
        for i in range(w):                                              # (R): nur über dem Ziel
            for j in range(h):
                e = [(x_index[(i, j, k, l, n, t)], 1.0) for k in range(w) if k != i for l in range(h) for n in range(t + 1, n_all + 1)]
                e += [(b_index[(i, j0, t, t)], -1.0) for j0 in range(j)]
                add(e, -np.inf, 0.0)
        for n in range(t + 1, n_all + 1):                               # (R): nur vom eigenen Platz
            for i in range(w):
                for j in range(h):
                    e = [(x_index[(i, j, k, l, n, t)], 1.0) for k in range(w) if k != i for l in range(h)]
                    e.append((b_index[(i, j, n, t)], -1.0))
                    add(e, -np.inf, 0.0)
        for i in range(w):                                              # (L)
            for k in range(w):
                if k == i:
                    continue
                for j in range(h):
                    for l in range(h):
                        e = [(v, factor) for v in xs[(i, j, k, l, t)]]
                        for jp in range(j + 1, h):
                            for lp in range(l + 1, h):
                                e += [(v, 1.0) for v in xs[(i, jp, k, lp, t)]]
                        add(e, -np.inf, rhs)
    for t in range(2, n_all + 1):                                       # (E)
        for n in range(t, n_all + 1):
            add([(b_index[(i, j, n, t)], 1.0) for i in range(w) for j in range(h)], 1.0, 1.0)
        for i in range(w):
            for j in range(h):
                add([(b_index[(i, j, n, t)], 1.0) for n in range(t, n_all + 1)], -np.inf, 1.0)
            for j in range(h - 1):
                add([(b_index[(i, j + 1, n, t)], 1.0) for n in range(t, n_all + 1)] + [(b_index[(i, j, n, t)], -1.0) for n in range(t, n_all + 1)], -np.inf, 0.0)
    c = np.zeros(nv)
    for v in x_index.values():
        c[v] = 1.0
    a = coo_matrix((vals, (rows, cols)), shape=(r[0], nv)).tocsr()
    return Model(c, a, np.array(lo), np.array(hi), lbv, ubv, b_index, x_index, w, h, n_all)


def lp_value(model: Model) -> tuple[float | None, float]:
    """(Wert der LP-Relaxation, Sekunden). None, wenn das LP nicht lösbar ist."""
    t0 = time.perf_counter()
    res = milp(model.c, constraints=LinearConstraint(model.a, model.lo, model.hi), integrality=np.zeros_like(model.c), bounds=Bounds(model.lb, model.ub), options={"disp": False})
    return (float(res.fun) if res.status == 0 else None), time.perf_counter() - t0
