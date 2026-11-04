"""Onglet Avions : âge et constructeur. Attention, une partie des avions est inconnue de la table planes."""

import pandas as pd
import plotly.graph_objects as go
from faicons import icon_svg
from shiny import module, render, ui
from shinywidgets import output_widget, render_plotly

from utils import NEUTRAL_COLOR, PROBLEM_COLOR, fmt_pct, style, summarise

INF = float("inf")
AGE_BINS = [-INF, 5, 10, 15, 20, INF]
AGE_LABELS = ["< 5 ans", "5–10 ans", "10–15 ans", "15–20 ans", "> 20 ans"]


def age_figure(df):
    d = df.dropna(subset=["plane_age"]).assign(
        bin=lambda x: pd.cut(x.plane_age, bins=AGE_BINS, labels=AGE_LABELS))
    d = summarise(d, "bin")
    fig = go.Figure(go.Bar(x=d.bin.astype(str), y=d.problem_rate, marker_color=PROBLEM_COLOR,
                           hovertemplate="%{x} : %{y:.1%}<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Âge de l'avion"), yaxis=dict(title="Taux de problèmes", tickformat=".0%"))
    return style(fig)


def manufacturer_figure(df, k: int = 8):
    d = summarise(df.dropna(subset=["manufacturer"]), "manufacturer").nlargest(k, "n").sort_values("problem_rate")
    fig = go.Figure(go.Bar(x=d.problem_rate, y=d.manufacturer, orientation="h", marker_color=NEUTRAL_COLOR,
                           hovertemplate="%{y} : %{x:.1%}<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Taux de problèmes", tickformat=".0%"))
    return style(fig)


@module.ui
def planes_ui():
    return ui.TagList(
        ui.value_box("Vols dont l'avion est connu (table planes)", ui.output_text("known"),
                     ui.p("AA et MQ déclarent des numéros de flotte, pas des immatriculations."),
                     showcase=icon_svg("circle-question")),
        ui.layout_columns(
            ui.card(ui.card_header("Selon l'âge de l'avion"), output_widget("by_age"), full_screen=True),
            ui.card(ui.card_header("Selon le constructeur (8 plus fréquents)"), output_widget("by_manufacturer"),
                    full_screen=True),
        ),
    )


@module.server
def planes_server(input, output, session, flights):
    @render.text
    def known():
        df = flights()
        return fmt_pct(df.plane_known.mean()) if len(df) else "–"

    @render_plotly
    def by_age():
        return age_figure(flights())

    @render_plotly
    def by_manufacturer():
        return manufacturer_figure(flights())
