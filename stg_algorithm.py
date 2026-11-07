"""Kern der Suche (Stück 5 und 6, verschlankt): IDA* mit Untergrenze und Zustandsmerken, dazu der Simulator, der eine Umlagerungsfolge nach den Regeln nachspielt.

Eine Bucht besteht aus Stapeln (Tupel von unten nach oben). Die Abrufnummer 1 kommt zuerst dran; nur der oberste Container eines Stapels ist erreichbar.
Liegt die nächste Nummer nicht oben, wird der oberste Container ihres Stapels (ein Blocker) auf einen anderen Stapel mit Platz gesetzt, jeder Hub kostet 1;
die nächste Nummer wird kostenlos entnommen, sobald sie oben liegt (restricted: nur Container über dem gesuchten werden bewegt).

  search   IDA*: Budget = Untergrenze der Wurzel, je Budget eine Tiefensuche mit Abbruch bei g + Untergrenze > Budget, am ersten Blatt zu Ende; Zustandsmerken je Stufe
           (kleinste Hubzahl je Zustand bis auf Vertauschen der Stapel). Knoten = Aufrufe der Suche, Summe über alle Stufen.
  replay   spielt Umlagerungen (Periode, Container, nach Stapel) nach den Regeln nach und gibt die Hubzahl zurück; wirft ValueError bei jedem Regelverstoß.
"""

from dataclasses import dataclass

INF = 10 ** 9


def autopop(stacks):
    """Ruft ab, was oben liegt und gerade dran ist. Gibt (neue Stapel, abgerufene Nummern in Reihenfolge) zurück."""
    st = [list(s) for s in stacks]
    popped = []
    while True:
        present = [c for s in st for c in s]
        if not present:
            return tuple(tuple(s) for s in st), popped
        t = min(present)
        for s in st:
            if s and s[-1] == t:
                s.pop()
                popped.append(t)
                break
        else:
            return tuple(tuple(s) for s in st), popped


def stack_blockers(stack):
    """Container in einem Stapel (unten nach oben), die über einem früher abzurufenden liegen."""
    total, lowest = 0, INF
    for c in stack:
        if c > lowest:
            total += 1
        else:
            lowest = c
    return total


def blocker_count(stacks):
    """Zahl der blockierenden Container (Untergrenze der Hubzahl, Stück 2)."""
    return sum(stack_blockers(s) for s in stacks)


def target_stack(stacks):
    """(nächste Abrufnummer, Index ihres Stapels). Die Bucht darf nicht leer sein."""
    t = min(c for s in stacks for c in s)
    for i, s in enumerate(stacks):
        if t in s:
            return t, i


def canon(stacks):
    """Kanonische Form: die Stapel sortiert."""
    return tuple(sorted(stacks))


def _fit_key(stacks, j, c):
    m = min(stacks[j]) if stacks[j] else INF
    return (0, m) if m > c else (1, -m)


def child_targets(stacks, src, height, c):
    """Zielstapel für den Blocker c (Stapel `src`, Bucht ohne c) in der Reihenfolge der engsten Passung (Stück 1); nur Stapel mit Platz."""
    dests = [j for j in range(len(stacks)) if j != src and len(stacks[j]) < height]
    dests.sort(key=lambda j: (_fit_key(stacks, j, c), j))
    return dests


@dataclass(frozen=True)
class SearchResult:
    optimum: int | None     # None, wenn das Knotenlimit erreicht wurde
    nodes: int              # Zahl der besuchten Knoten (bei capped: das Limit); Summe über alle Budgetstufen
    capped: bool
    stages: int             # Zahl der Budgetstufen (bei capped: die begonnenen)


class _CapReached(Exception):
    pass


class _Found(Exception):
    pass


def search(stacks, height, cap=1_000_000) -> SearchResult:
    """IDA* mit Untergrenze und Zustandsmerken (kanonisch), engste Passung zuerst."""
    start = tuple(tuple(s) for s in stacks)
    budget = blocker_count(start)
    total, stages = 0, 0
    while True:
        stages += 1
        b = budget
        nodes = [0]
        table = {}
        found = []

        def rec(state, g):
            nodes[0] += 1
            if total + nodes[0] > cap:
                raise _CapReached
            st, _ = autopop(state)
            if not any(st):
                found.append(g)
                raise _Found
            if g + blocker_count(st) > b:
                return
            key = canon(st)
            if table.get(key, INF) <= g:
                return
            table[key] = g
            _, i = target_stack(st)
            lst = [list(s) for s in st]
            c = lst[i].pop()
            base = tuple(tuple(s) for s in lst)
            for j in child_targets(base, i, height, c):
                nxt = [list(s) for s in lst]
                nxt[j].append(c)
                rec(tuple(tuple(s) for s in nxt), g + 1)

        try:
            rec(start, 0)
        except _Found:
            pass
        except _CapReached:
            return SearchResult(None, cap, True, stages)
        total += nodes[0]
        if found:
            return SearchResult(found[0], total, False, stages)
        budget += 1


def replay(bay, height, moves):
    """Spielt eine Umlagerungsfolge nach den Regeln nach. `moves`: Liste (Periode t, Container, Zielstapel k) in der Reihenfolge der Ausführung (je Periode von oben nach unten).
    Regeln: In Periode t (Abruf des Containers t) darf nur der oberste Container des Stapels bewegt werden, in dem t liegt, und nur, wenn er über t liegt; der Zielstapel
    ist ein anderer Stapel mit Platz; danach muss t oben liegen und wird abgerufen. Gibt die Zahl der Umlagerungen zurück (bei vollständigem Abruf), sonst ValueError."""
    st = [list(s) for s in bay]
    n = sum(len(s) for s in st)
    hubs = 0
    pending = list(moves)
    for t in range(1, n + 1):
        src = next(i for i, s in enumerate(st) if t in s)
        while pending and pending[0][0] == t:
            _, c, k = pending.pop(0)
            if not st[src] or st[src][-1] != c:
                raise ValueError(f"Periode {t}: Container {c} liegt nicht oben im Stapel {src + 1}")
            if c == t:                                                  # der oberste Container des Zielstapels ist das Ziel selbst: es gibt nichts zu bewegen
                raise ValueError(f"Periode {t}: Container {c} liegt nicht über dem Ziel")
            if k == src or not 0 <= k < len(st) or len(st[k]) >= height:
                raise ValueError(f"Periode {t}: Container {c} kann nicht auf Stapel {k + 1}")
            st[k].append(st[src].pop())
            hubs += 1
        if st[src][-1] != t:
            raise ValueError(f"Periode {t}: Container {t} liegt nicht oben")
        st[src].pop()
    if pending:
        raise ValueError("übrige Umlagerungen nach dem letzten Abruf")
    if any(st):
        raise ValueError("Bucht nicht leer")
    return hubs
