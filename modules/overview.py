import plotly.graph_objects as go
from faicons import icon_svg
from shiny import module, reactive, render, ui
from shinywidgets import output_widget, render_plotly

from utils import MOIS, NEUTRAL_COLOR, PROBLEM_COLOR, fmt_int, fmt_min, fmt_pct, kpis, style, summarise


def monthly_figure(df):
    d = summarise(df, "month")
    x = [MOIS[int(m) - 1] for m in d.month]
    fig = go.Figure()
    fig.add_bar(x=x, y=d.n, name="Vols", marker_color=NEUTRAL_COLOR)
    fig.add_scatter(x=x, y=d.problem_rate, name="Taux de problèmes", yaxis="y2",
                    mode="lines+markers", line=dict(color=PROBLEM_COLOR, width=3))
    fig.update_layout(
        yaxis=dict(title="Vols"),
        yaxis2=dict(title="Taux de problèmes", overlaying="y", side="right",
                    tickformat=".0%", rangemode="tozero", showgrid=False),
    )
    return style(fig)


@module.ui
def overview_ui():
    return ui.TagList(
        ui.layout_column_wrap(
            ui.value_box("Vols", ui.output_text("n"), showcase=icon_svg("plane")),
            ui.value_box("Taux d'annulation", ui.output_text("cancel"), showcase=icon_svg("ban"), theme="danger"),
            ui.value_box("Vols en retard (> 15 min)", ui.output_text("delay"), showcase=icon_svg("clock"), theme="warning"),
            ui.value_box("Retard moyen à l'arrivée", ui.output_text("avg"), showcase=icon_svg("hourglass-half")),
            width="220px",
            fill=False,
        ),
        ui.card(ui.card_header("Volume et taux de problèmes par mois"), output_widget("monthly"), full_screen=True),
        ui.p("« Problème » = retard à l'arrivée > 15 min, annulation ou déroutement.", class_="text-muted small"),
    )


@module.server
def overview_server(input, output, session, flights):
    @reactive.calc
    def k():
        return kpis(flights())

    @render.text
    def n():
        return fmt_int(k()["n"])

    @render.text
    def cancel():
        return fmt_pct(k()["cancel_rate"])

    @render.text
    def delay():
        return fmt_pct(k()["delay_rate"])

    @render.text
    def avg():
        return fmt_min(k()["avg_arr_delay"])

    @render_plotly
    def monthly():
        return monthly_figure(flights())
