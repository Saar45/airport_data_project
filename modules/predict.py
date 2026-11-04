"""Onglet Prédiction : probabilité de problème pour un scénario donné (ignore les filtres globaux)."""

import pandas as pd
import plotly.graph_objects as go
from faicons import icon_svg
from shiny import module, reactive, render, ui
from shinywidgets import output_widget, render_plotly

from model import predict_problem
from utils import MOIS, PROBLEM_COLOR, fmt_pct, style

HOURS = list(range(5, 24))


def hourly_figure(model, scenario: pd.DataFrame, current_hour: int):
    s = pd.concat([scenario] * len(HOURS), ignore_index=True).assign(hour=HOURS)
    p = predict_problem(model, s)
    fig = go.Figure(go.Scatter(x=HOURS, y=p, mode="lines+markers", line=dict(color=PROBLEM_COLOR),
                               hovertemplate="%{x}h : %{y:.1%}<extra></extra>"))
    fig.add_vline(x=current_hour, line_dash="dot")
    fig.add_hline(y=model["base_rate"], line_dash="dash", annotation_text="moyenne historique")
    fig.update_layout(xaxis=dict(title="Heure de départ prévue", dtick=1),
                      yaxis=dict(title="Probabilité de problème", tickformat=".0%", rangemode="tozero"))
    return style(fig)


@module.ui
def predict_ui(model, carrier_choices: dict):
    lv = model["levels"]
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("carrier", "Compagnie", {c: carrier_choices.get(c, c) for c in lv["carrier"]}),
            ui.input_select("origin", "Aéroport d'origine", lv["origin"]),
            ui.input_select("month", "Mois", {m: MOIS[int(m) - 1] for m in lv["month"]}),
            ui.input_slider("hour", "Heure de départ prévue", 5, 23, 17),
            ui.input_slider("visib", "Visibilité (miles)", 0, 10, 10, step=0.5),
            ui.input_slider("wind_speed", "Vent (mph)", 0, 40, 10),
            ui.input_slider("precip", "Précipitations (pouces/h)", 0, 1, 0, step=0.01),
            title="Scénario",
            width=300,
        ),
        ui.layout_column_wrap(
            ui.value_box("Probabilité de problème", ui.output_text("prob"),
                         showcase=icon_svg("triangle-exclamation"), theme="danger"),
            ui.value_box("Moyenne historique", fmt_pct(model["base_rate"]), showcase=icon_svg("chart-line")),
            width="250px",
            fill=False,
        ),
        ui.card(ui.card_header("Probabilité selon l'heure de départ (autres paramètres fixés)"),
                output_widget("by_hour"), full_screen=True),
        ui.p(f"Modèle de démonstration : régression logistique, AUC sur jeu de test = "
             f"{model['auc']:.2f}".replace(".", ",") + ". "
             f"Météo connue pour {fmt_pct(model['weather_coverage'], 0)} des vols d'entraînement : "
             "l'effet de la météo est appris sur ces vols uniquement. À améliorer.",
             class_="text-muted small"),
        fillable=False,
    )


@module.server
def predict_server(input, output, session, model):
    @reactive.calc
    def scenario():
        return pd.DataFrame([{
            "carrier": input.carrier(), "origin": input.origin(), "month": input.month(),
            "hour": input.hour(), "visib": input.visib(),
            "wind_speed": input.wind_speed(), "precip": input.precip(),
        }])

    @render.text
    def prob():
        return fmt_pct(predict_problem(model, scenario())[0])

    @render_plotly
    def by_hour():
        return hourly_figure(model, scenario(), input.hour())
