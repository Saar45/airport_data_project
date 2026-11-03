"""Onglet Carte : destinations, taille = volume, couleur = taux de problèmes."""

import numpy as np
import plotly.graph_objects as go
from shiny import module, ui
from shinywidgets import output_widget, render_plotly

from utils import COLORSCALE, fmt_int, fmt_pct, summarise


def map_figure(df, airports):
    d = summarise(df, ["dest", "dest_name"]).merge(
        airports[["faa", "lat", "lon"]].rename(columns={"faa": "dest"}), on="dest", how="inner"
    ).dropna(subset=["lat", "lon"])
    size = 6 + 30 * np.sqrt(d.n / d.n.max()) if len(d) else []
    fig = go.Figure(go.Scattermap(
        lat=d.lat, lon=d.lon, mode="markers",
        # cmax au 95e centile : quelques petites routes à 100 % écraseraient l'échelle.
        marker=dict(size=size, color=d.problem_rate, colorscale=COLORSCALE, opacity=0.85,
                    cmin=0, cmax=d.problem_rate.quantile(0.95) if len(d) else 1,
                    colorbar=dict(title="Problèmes", tickformat=".0%")),
        text=[f"{name} ({code})<br>{fmt_int(n)} vols · {fmt_pct(r)} de problèmes"
              for name, code, n, r in zip(d.dest_name, d.dest, d.n, d.problem_rate)],
        hoverinfo="text",
    ))
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=38, lon=-95), zoom=2.6),
                      margin=dict(l=0, r=0, t=0, b=0), height=600)
    return fig


@module.ui
def map_ui():
    return ui.card(ui.card_header("Destinations au départ de New York"), output_widget("map"), full_screen=True)


@module.server
def map_server(input, output, session, flights, airports):
    @render_plotly
    def map():
        return map_figure(flights(), airports)
