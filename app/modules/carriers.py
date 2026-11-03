"""Onglet « Compagnies & routes » : qui concentre les problèmes ?"""

import pandas as pd
import plotly.graph_objects as go
from shiny import module, render, ui
from shinywidgets import output_widget, render_plotly

from utils import PROBLEM_COLOR, style, summarise


def carriers_figure(df, min_flights: int = 100):
    d = summarise(df, ["carrier", "carrier_name"])
    d = d[d.n >= min_flights].sort_values("problem_rate")
    fig = go.Figure(go.Bar(
        x=d.problem_rate, y=d.carrier_name, orientation="h", marker_color=PROBLEM_COLOR,
        customdata=d[["n", "cancel_rate"]],
        hovertemplate="%{y}<br>Problèmes : %{x:.1%}<br>Annulations : %{customdata[1]:.1%}"
                      "<br>Vols : %{customdata[0]:,}<extra></extra>",
    ))
    fig.update_layout(xaxis=dict(title="Taux de problèmes", tickformat=".0%"), height=500)
    return style(fig)


def routes_table(df, min_flights: int = 100) -> pd.DataFrame:
    d = summarise(df, ["origin", "dest", "dest_name"])
    d = d[d.n >= min_flights].sort_values("problem_rate", ascending=False)
    return pd.DataFrame({
        "Origine": d.origin,
        "Destination": d.dest_name + " (" + d.dest + ")",
        "Vols": d.n,
        "Problèmes (%)": (100 * d.problem_rate).round(1),
        "Annulations (%)": (100 * d.cancel_rate).round(1),
        "Retard moyen (min)": d.avg_arr_delay.round(1),
    })


@module.ui
def carriers_ui():
    return ui.layout_columns(
        ui.card(ui.card_header("Taux de problèmes par compagnie (≥ 100 vols)"),
                output_widget("by_carrier"), full_screen=True),
        ui.card(ui.card_header("Routes les plus problématiques (≥ 100 vols)"),
                ui.output_data_frame("routes"), full_screen=True),
        col_widths=(5, 7),
    )


@module.server
def carriers_server(input, output, session, flights):
    @render_plotly
    def by_carrier():
        return carriers_figure(flights())

    @render.data_frame
    def routes():
        return render.DataGrid(routes_table(flights()), filters=True)
