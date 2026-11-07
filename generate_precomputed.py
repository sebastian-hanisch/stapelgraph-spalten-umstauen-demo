"""Erzeugt stg_bands.json: Kennzahlen der festen Buchten (Seeds ab 0, Platz 2) für zwei Auswertungen.

    python generate_precomputed.py

"zellen":    je Zelle Größe der Stapelgraphen, Stärke der Schranke (Spalten-LP gegen kompaktes LP und Optimum) und, wo die Spaltengenerierung gerechnet wird (stg_constants.CG_CELLS),
             Iterationen, Spalten, Anteil des Preisproblems und die im Wurzelknoten bewiesenen Buchten; 3 x 4 mit dem vollen Pfadfluss statt der Spaltengenerierung (SIZE_CELLS).
"korrektur": je Zelle der Master ohne die Ordnungsbedingung (O) (FIX_CELLS).

Rechenzeit rund 10 bis 15 Minuten (4 x 3 mit Spaltengenerierung und 3 x 4 mit dem vollen Pfadfluss sind die teuren Zellen; die Zellen laufen in getrennten Prozessen, die Zeiten
sind deshalb Einzelmessungen unter Last und schwanken). Dieselben Funktionen wie die Tests (`stg_evaluation.cell_rows`, `cell_stats`, `fix_rows`, `fix_stats`); die Datei speichert
nur Kennzahlen, keine Zeilen. tests/test_presets.py rechnet kleine Zellen neu und vergleicht, was nicht von der Zeit abhängt."""

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import stg_constants as C
import stg_evaluation as ev

sys.stdout.reconfigure(encoding="utf-8")


def job(kind, stacks, layers, n, use_cg):
    seeds = range(n)
    if kind == "korrektur":
        return kind, stacks, layers, ev.fix_stats(ev.fix_rows(stacks, layers, C.DEFAULT_EXTRA, seeds))
    return kind, stacks, layers, ev.cell_stats(ev.cell_rows(stacks, layers, C.DEFAULT_EXTRA, seeds, use_cg), stacks, layers)


def main():
    cg_cells = {(s, l) for s, l, _ in C.CG_CELLS}
    tasks = [("zellen", s, l, n, (s, l) in cg_cells) for s, l, n in C.SIZE_CELLS] + [("korrektur", s, l, n, False) for s, l, n in C.FIX_CELLS]
    tasks.sort(key=lambda t: -(t[1] * t[2]) ** 2 * (1 if t[0] == "korrektur" else 3))                 # die teuren Zellen zuerst
    bands = {"zellen": {}, "korrektur": {}}
    with ProcessPoolExecutor(max_workers=max(2, min(6, (os.cpu_count() or 2) - 1))) as pool:
        futures = [pool.submit(job, *t) for t in tasks]
        for f in as_completed(futures):
            kind, stacks, layers, stats = f.result()
            bands[kind][ev.cell_key(stacks, layers)] = stats
            print(f"{kind} {stacks} x {layers}: fertig", flush=True)
    ev.BANDS_FILE.write_text(json.dumps(bands, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("geschrieben:", ev.BANDS_FILE.name)


if __name__ == "__main__":
    main()
