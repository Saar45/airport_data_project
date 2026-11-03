"""Onglet « Quand ? » : à quels moments les problèmes surviennent-ils ?"""

import pandas as pd
import plotly.graph_objects as go
from shiny import module, reactive, render, ui
from shinywidgets import output_widget, render_plotly

from utils import COLORSCALE, PROBLEM_COLOR, style, summarise


def heatmap_figure(df, min_flights: int = 20):
    d = summarise(df, ["wday", "hour"])
    d = d[d.n >= min_flights]
    pivot = d.pivot(index="wday", columns="hour", values="problem_rate")
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index.astype(str),
        colorscale=COLORSCALE, colorbar=dict(tickformat=".0%"),
        hovertemplate="%{y} %{x}h : %{z:.1%}<extra></extra>",
    ))
    fig.update_layout(xaxis=dict(title="Heure de départ prévue", dtick=1), yaxis=dict(autorange="reversed"))
    return style(fig)


def daily_figure(daily: pd.DataFrame):
    fig = go.Figure(go.Scatter(
        x=daily.date, y=daily.problem_rate, mode="lines", line=dict(color=PROBLEM_COLOR),
        hovertemplate="%{x|%d/%m/%Y} : %{y:.1%}<extra></extra>",
    ))
    fig.update_layout(yaxis=dict(title="Taux de problèmes", tickformat=".0%"))
    return style(fig)


def worst_days_table(daily: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    d = daily[daily.n >= 50].nlargest(k, "problem_rate")
    return pd.DataFrame({
        "Date": d.date.dt.strftime("%d/%m/%Y"),
        "Vols": d.n,
        "Problèmes (%)": (100 * d.problem_rate).round(1),
        "Annulations (%)": (100 * d.cancel_rate).round(1),
    })


@module.ui
def temporal_ui():
    return ui.TagList(
        ui.card(ui.card_header("Taux de problèmes par jour de la semaine et heure prévue"),
                output_widget("heatmap"), full_screen=True),
        ui.layout_columns(
            ui.card(ui.card_header("Taux de problèmes jour par jour"), output_widget("daily"), full_screen=True),
            ui.card(ui.card_header("10 jours les plus critiques"), ui.output_data_frame("worst")),
            col_widths=(8, 4),
        ),
    )


@module.server
def temporal_server(input, output, session, flights):
    @reactive.calc
    def daily_stats():
        return summarise(flights(), "date")

    @render_plotly
    def heatmap():
        return heatmap_figure(flights())

    @render_plotly
    def daily():
        return daily_figure(daily_stats())

    @render.data_frame
    def worst():
        return worst_days_table(daily_stats())
