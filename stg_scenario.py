"""Szenario: Buchten für das Umstauen. Eine Bucht ist ein Tupel von Stapeln (von unten nach oben) mit den Abrufnummern 1 bis N."""

import random


def make_bay(stacks: int, layers: int, seed: int) -> tuple:
    """Volle Bucht: `stacks` Stapel mit je `layers` Containern, die Abrufnummern 1 bis stacks * layers zufällig verteilt.
    Deterministisch aus (stacks, layers, seed): gleiche Eingabe, gleiche Bucht (wie in Stück 1 der Reihe)."""
    n = stacks * layers
    perm = list(range(1, n + 1))
    random.Random(seed).shuffle(perm)
    return tuple(tuple(perm[i * layers:(i + 1) * layers]) for i in range(stacks))


def max_height(layers: int, extra: int) -> int:
    """Höchsthöhe eines Stapels: die Anfangsfüllung plus `extra` Lagen Platz."""
    return layers + extra


def partial_bay(stacks: int, height: int, n: int, seed: int) -> tuple:
    """Teilgefüllte Zufallsbucht: `n` Container mit den Nummern 1 bis n, jeder auf einen zufällig gewählten Stapel mit freiem Platz.
    Die Stapel sind danach ungleich hoch (andere Familie als `make_bay`). Verlangt n <= (stacks - 1) * height: dann finden die
    Container über einem Ziel immer einen Ausweichplatz."""
    if not 1 <= n <= (stacks - 1) * height:
        raise ValueError("n muss zwischen 1 und (Stapel - 1) * Höchsthöhe liegen")
    rng = random.Random(seed)
    perm = list(range(1, n + 1))
    rng.shuffle(perm)
    st = [[] for _ in range(stacks)]
    for c in perm:
        free = [i for i in range(stacks) if len(st[i]) < height]
        st[rng.choice(free)].append(c)
    return tuple(tuple(s) for s in st)


def canonical(bay: tuple) -> tuple:
    """Bucht bis auf Vertauschen der Stapel (die Reihenfolge der Stapel spielt für die Kosten keine Rolle)."""
    return tuple(sorted(bay))
