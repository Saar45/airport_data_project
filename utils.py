"""Constantes, formatage et agrégats partagés par tous les onglets."""

import math

import pandas as pd

JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
MOIS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]

PROBLEM_COLOR = "#d9534f"
NEUTRAL_COLOR = "#9fb3c8"
COLORSCALE = [[0, "#ffffcc"], [0.5, "#fd8d3c"], [1, "#bd0026"]]


def fmt_pct(x, digits: int = 1) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    return f"{100 * x:.{digits}f} %".replace(".", ",")


def fmt_int(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def fmt_min(x) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    return f"{round(x, 1) + 0.0:.1f} min".replace(".", ",")  # + 0.0 évite l'affichage « -0,0 »


def summarise(df: pd.DataFrame, by=None) -> pd.DataFrame:
    """Indicateurs de problèmes, globaux (by=None) ou par groupe."""
    g = df.groupby(by, observed=True) if by is not None else df.assign(_all=0).groupby("_all")
    out = g.agg(
        n=("problem", "size"),
        cancel_rate=("cancelled", "mean"),
        problem_rate=("problem", "mean"),
        avg_arr_delay=("arr_delay", "mean"),
        n_delayed=("delayed", "sum"),
        n_flown=("flown", "sum"),
    ).reset_index()
    out["delay_rate"] = out.n_delayed / out.n_flown.clip(lower=1)
    return out.drop(columns="_all", errors="ignore")


def kpis(df: pd.DataFrame) -> dict:
    s = summarise(df)
    if s.empty:
        return {"n": 0, "cancel_rate": math.nan, "delay_rate": math.nan,
                "problem_rate": math.nan, "avg_arr_delay": math.nan}
    return s.iloc[0].to_dict()


def html_table(df: pd.DataFrame, max_height: int | None = None):
    """Petit tableau statique (Bootstrap). Pour les gros tableaux interactifs, utiliser render.data_frame."""
    from shiny import ui

    table = ui.HTML(df.to_html(index=False, border=0, na_rep="–",
                               classes="table table-sm table-striped table-hover mb-0"))
    style_ = f"max-height:{max_height}px; overflow-y:auto;" if max_height else ""
    return ui.div(table, style=style_ + "overflow-x:auto;")


def style(fig):
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=-0.15),
        separators=", ",
    )
    return fig
