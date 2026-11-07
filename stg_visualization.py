"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben."""

import plotly.graph_objects as go

import stg_algorithm as A
import stg_constants as C


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=340):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.25), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def blocker_cells(stacks) -> set:
    """Container, die über einem früher abzurufenden im selben Stapel liegen (Position (Stapel, Lage))."""
    out = set()
    for i, s in enumerate(stacks):
        lowest = A.INF
        for j, c in enumerate(s):
            if c > lowest:
                out.add((i, j))
            else:
                lowest = c
    return out


def build_bay(stacks, height, target=None):
    """Die Bucht als Säulen: je Lage ein Balken mit der Abrufnummer. Rot: blockiert einen früher abzurufenden, grün: nächster Abruf
    (`target`, eine Abrufnummer oder None), grau-blau: übrige."""
    blockers = blocker_cells(stacks)
    fig = go.Figure()
    xs = list(range(len(stacks)))
    for j in range(height):
        ys, colors, texts = [], [], []
        for i, s in enumerate(stacks):
            if j < len(s):
                c = s[j]
                ys.append(1)
                texts.append(str(c))
                colors.append(C.COLOR_TARGET if c == target else C.COLOR_BLOCK if (i, j) in blockers else C.COLOR_CELL)
            else:
                ys.append(0)
                texts.append("")
                colors.append(C.COLOR_CELL)
        fig.add_trace(go.Bar(x=xs, y=ys, base=j, marker_color=colors, text=texts, textposition="inside", insidetextanchor="middle",
                             textfont=dict(color="#ffffff", size=16), width=0.78, showlegend=False,
                             hovertemplate="Abruf %{text}<extra></extra>", marker_line=dict(width=0)))
    fig.update_layout(barmode="overlay")
    fig.add_hline(y=height, line_dash="dot", line_color="rgba(128,128,128,0.7)", annotation_text="Höchsthöhe", annotation_position="top left")
    fig.update_xaxes(tickvals=xs, ticktext=[f"Stapel {i + 1}" for i in xs], showgrid=False)
    fig.update_yaxes(range=[0, height + 0.35], showticklabels=False, showgrid=False, zeroline=False)
    return _base(fig, height=48 * height + 90)


def build_stack_sizes(sizes):
    """Kanten der Stapelgraphen je Stapel einer Bucht als Balken (logarithmisch). `sizes`: [(Knoten, Kanten)] je Stapel."""
    names = [f"Stapel {i + 1}" for i in range(len(sizes))]
    fig = go.Figure(go.Bar(x=names, y=[a for _, a in sizes], marker_color=C.COLOR_GRAPH, text=[f"{a:,}".replace(",", " ") for _, a in sizes], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{text} Kanten<extra></extra>"))
    fig.update_xaxes(type="category")
    fig.update_yaxes(title_text="Kanten des Stapelgraphen (logarithmisch)", type="log")
    return _base(fig, height=300)


def build_size(cells):
    """Kanten der Stapelgraphen (Median, Maximum) gegen die Variablen des kompakten Modells je Zelle, nach Containerzahl geordnet (logarithmisch). `cells`: {Zellname: cell_stats}."""
    names = sorted(cells, key=lambda n: (cells[n]["containers"], cells[n]["compact_vars"]))
    x = [f"{n} ({cells[n]['containers']})" for n in names]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=[cells[n]["arcs"]["median"] for n in names], name="Stapelgraphen, Kanten (Median)", marker_color=C.COLOR_GRAPH, hovertemplate="%{x}: %{y:,.0f}<extra>%{fullData.name}</extra>"))
    fig.add_trace(go.Bar(x=x, y=[cells[n]["arcs"]["max"] for n in names], name="Stapelgraphen, Kanten (Maximum)", marker_color=C.COLOR_COLUMNS, hovertemplate="%{x}: %{y:,.0f}<extra>%{fullData.name}</extra>"))
    fig.add_trace(go.Bar(x=x, y=[cells[n]["compact_vars"] for n in names], name="kompaktes Modell, Variablen", marker_color=C.COLOR_COMPACT, hovertemplate="%{x}: %{y:,.0f}<extra>%{fullData.name}</extra>"))
    fig.update_layout(barmode="group")
    fig.update_xaxes(type="category", title_text="Zelle (Container)")
    fig.update_yaxes(title_text="Anzahl (logarithmisch)", type="log")
    return _base(fig, height=380)


def build_strength(cells):
    """Buchten, in denen das Spalten-LP und das kompakte LP das Optimum treffen, und in denen das Spalten-LP strikt stärker ist, als Anteil je Zelle (Prozent). `cells`: {Zellname: cell_stats}."""
    names = list(cells)
    fig = go.Figure()
    for label, key, color in (("kompaktes LP trifft das Optimum", "compact_equal", C.COLOR_COMPACT), ("Spalten-LP trifft das Optimum", "cols_equal", C.COLOR_GRAPH),
                              ("Spalten-LP strikt stärker", "stronger", C.COLOR_COLUMNS)):
        fig.add_trace(go.Bar(x=names, y=[100.0 * cells[n][key] / cells[n]["n"] for n in names], name=label, marker_color=color, hovertemplate="%{x}: %{y:.0f} %<extra>%{fullData.name}</extra>"))
    fig.update_layout(barmode="group")
    fig.update_xaxes(type="category")
    fig.update_yaxes(title_text="Anteil der Buchten (%)", range=[0, 105])
    return _base(fig, height=340)


def build_columns(cells):
    """Erzeugte Spalten (Median) gegen Kanten (Median) je Zelle der Spaltengenerierung (logarithmisch). `cells`: {Zellname: cell_stats} nur mit Spaltengenerierung."""
    names = sorted((n for n in cells if "cg" in cells[n]), key=lambda n: cells[n]["containers"])
    x = [f"{n} ({cells[n]['containers']})" for n in names]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=[cells[n]["arcs"]["median"] for n in names], name="Kanten der Stapelgraphen", marker_color=C.COLOR_GRAPH, hovertemplate="%{x}: %{y:,.0f}<extra>%{fullData.name}</extra>"))
    fig.add_trace(go.Bar(x=x, y=[cells[n]["cg"]["columns"]["median"] for n in names], name="erzeugte Spalten", marker_color=C.COLOR_COLUMNS, hovertemplate="%{x}: %{y:,.0f}<extra>%{fullData.name}</extra>"))
    fig.update_layout(barmode="group")
    fig.update_xaxes(type="category", title_text="Zelle (Container)")
    fig.update_yaxes(title_text="Median (logarithmisch)", type="log")
    return _base(fig, height=340)
