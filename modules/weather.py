"""Onglet Météo : impact des conditions à l'aéroport de départ."""

import pandas as pd
import plotly.graph_objects as go
from shiny import module, render, ui
from shinywidgets import output_widget, render_plotly

from utils import MOIS, PROBLEM_COLOR, fmt_int, fmt_pct, style, summarise

INF = float("inf")
WEATHER_VARS = {
    "visib": dict(label="Visibilité (miles)", bins=[-INF, 1, 3, 5, 9.99, INF],
                  labels=["< 1", "1–3", "3–5", "5–10", "10 (dégagé)"]),
    "wind_speed": dict(label="Vent (mph)", bins=[-INF, 5, 10, 15, 20, 25, INF],
                       labels=["0–5", "5–10", "10–15", "15–20", "20–25", "> 25"]),
    "precip": dict(label="Précipitations (pouces/h)", bins=[-INF, 0, 0.05, 0.1, 0.25, INF],
                   labels=["Aucune", "≤ 0,05", "0,05–0,1", "0,1–0,25", "> 0,25"]),
    "temp": dict(label="Température", bins=[-INF, 32, 50, 68, 86, INF],
                 labels=["< 0 °C", "0–10 °C", "10–20 °C", "20–30 °C", "> 30 °C"]),
}


def weather_figure(df, var: str):
    cfg = WEATHER_VARS[var]
    d = df.dropna(subset=[var]).assign(bin=lambda x: pd.cut(x[var], bins=cfg["bins"], labels=cfg["labels"]))
    d = summarise(d, "bin")
    fig = go.Figure(go.Bar(
        x=d.bin.astype(str), y=d.problem_rate, marker_color=PROBLEM_COLOR,
        text=[f"{n:,} vols".replace(",", " ") for n in d.n], textposition="outside",
        hovertemplate="%{x} : %{y:.1%}<extra></extra>",
    ))
    fig.update_layout(xaxis=dict(title=cfg["label"]), yaxis=dict(title="Taux de problèmes", tickformat=".0%"))
    return style(fig)


def coverage_text(df, var: str) -> str:
    """Part des vols filtrés qui ont une valeur météo, et pour quels aéroports / mois."""
    known = df.dropna(subset=[var])
    if known.empty:
        return "Aucun vol de la sélection n'a de donnée météo."
    months = sorted(int(m) for m in known.month.unique())
    return (f"Météo connue pour {fmt_pct(len(known) / len(df), 0)} des vols de la sélection "
            f"({fmt_int(len(known))} vols, aéroports : {', '.join(sorted(known.origin.unique()))}, "
            f"mois : {MOIS[months[0] - 1]}–{MOIS[months[-1] - 1]}). "
            "Météo mesurée à l'aéroport de départ.")


@module.ui
def weather_ui():
    return ui.card(
        ui.card_header("Taux de problèmes selon la météo au départ"),
        ui.input_select("var", "Variable", {k: v["label"] for k, v in WEATHER_VARS.items()}),
        output_widget("by_weather"),
        ui.p(ui.output_text("coverage", inline=True), class_="text-muted small"),
        full_screen=True,
    )


@module.server
def weather_server(input, output, session, flights):
    @render_plotly
    def by_weather():
        return weather_figure(flights(), input.var())

    @render.text
    def coverage():
        return coverage_text(flights(), input.var())
