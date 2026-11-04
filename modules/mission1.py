"""Onglet Mission 1 : les 8 questions d'exploration (notebook Mission1_Exploration.ipynb).

Les réponses sont recalculées à partir des données de l'app (Supabase), avec la même logique
que le notebook. Cet onglet ignore les filtres globaux : ce sont des réponses sur toute la base.
"""

import pandas as pd
import plotly.graph_objects as go
from shiny import module, render, ui
from shinywidgets import output_widget, render_plotly

from data_prep import MISSING_AIRPORTS, added_planes_mask
from utils import NEUTRAL_COLOR, fmt_int, fmt_pct, html_table, style

ADDED_AIRPORTS = list(MISSING_AIRPORTS.faa)
ORIGIN_COLORS = {"EWR": "#4C78A8", "JFK": "#F58518", "LGA": "#54A24B"}
MAJORS = {"UA": "United", "AA": "American", "DL": "Delta"}
PREVIEW_ROWS = 1000


# ---------------------------------------------------------------- calculs (fonctions pures)

def q1_table(app) -> pd.DataFrame:
    f, ap = app["flights"], app["raw"]["airports"]
    airlines, planes = app["raw"]["airlines"], app["raw"]["planes"]
    orig = ap[~ap.faa.isin(ADDED_AIRPORTS)]          # table airports telle que dans le fichier fourni
    added = sorted(ap.faa[ap.faa.isin(ADDED_AIRPORTS)])
    n_dst, n_dst0 = int((ap.dst == "N").sum()), int((orig.dst == "N").sum())
    n_tz, n_tz_na = ap.tzone.nunique(), int(ap.tzone.isna().sum())
    n_tz0 = orig.tzone.nunique() + (1 if orig.tzone.isna().any() else 0)
    new_tz = sorted(set(ap.tzone.dropna()) - set(orig.tzone.dropna()))
    added_note = f"ajoutés en Mission 2 : {', '.join(added)}" if added else ""
    tz_detail = [f"Fichier fourni : {n_tz0} en comptant la valeur manquante « \\N » comme l'énoncé"
                 + (f" ({n_tz_na} aéroports, désormais NULL)" if n_tz_na else "") + "."]
    if new_tz:
        tz_detail.append(f"Apportés par les aéroports ajoutés : {', '.join(new_tz)}.")
    n_added_planes = int(added_planes_mask(planes).sum())
    planes_detail = (f"{fmt_int(len(planes) - n_added_planes)} dans le fichier fourni (valeur de l'énoncé) + "
                     f"{fmt_int(n_added_planes)} ajoutés en Mission 2 sans caractéristiques. "
                     if n_added_planes else "")
    planes_detail += f"{fmt_int(f.tailnum.nunique())} immatriculations différentes dans flights."

    rows = [
        ("Aéroports (table airports)", fmt_int(ap.faa.nunique()),
         f"{fmt_int(len(orig))} dans le fichier fourni + {len(added)} {added_note}" if added else ""),
        ("Aéroports de départ", fmt_int(f.origin.nunique()), ", ".join(sorted(f.origin.unique()))),
        ("Aéroports de destination", fmt_int(f.dest.nunique()), ""),
        ("Aéroports sans heure d'été (dst = N)", fmt_int(n_dst),
         f"{n_dst0} dans le fichier fourni (valeur de l'énoncé) + {n_dst - n_dst0} {added_note}"
         if n_dst != n_dst0 else ""),
        ("Fuseaux horaires (tzone)", fmt_int(n_tz), " ".join(tz_detail)),
        ("Compagnies", fmt_int(airlines.carrier.nunique()), ""),
        ("Avions (table planes)", fmt_int(planes.tailnum.nunique()), planes_detail),
        ("Vols annulés", fmt_int(f.cancelled.sum()),
         f"{fmt_pct(f.cancelled.mean(), 2)} des vols : heure de départ réelle (dep_time) vide"),
    ]
    return pd.DataFrame(rows, columns=["Indicateur", "Valeur", "Détail"])


def origins_table(f, airports) -> pd.DataFrame:
    names = airports.set_index("faa").name
    d = f.origin.value_counts()
    return pd.DataFrame({"Code": d.index, "Aéroport": d.index.map(names), "Vols": d.map(fmt_int).values,
                         "% des vols": [fmt_pct(x, 2) for x in d.values / len(f)]})


def destinations_table(f, order: str = "top", k: int = 10) -> pd.DataFrame:
    d = f.groupby(["dest", "dest_name"]).size().rename("n").reset_index()
    d["pct"] = d.n / d.n.sum()
    d = d.nlargest(k, "n") if order == "top" else d.nsmallest(k, "n").sort_values("n", ascending=False)
    digits = 2 if order == "top" else 4   # 1 vol sur 250 000 ≈ 0,0004 %
    return pd.DataFrame({"Code": d.dest, "Destination": d.dest_name, "Vols": d.n.map(fmt_int),
                         "% des vols": d.pct.map(lambda x: fmt_pct(x, digits))})


def planes_table(f, planes, order: str = "top", k: int = 10) -> pd.DataFrame:
    s = (f.dropna(subset=["tailnum"]).groupby("tailnum")
          .agg(vols=("tailnum", "size"), compagnie=("carrier_name", lambda x: ", ".join(sorted(x.unique()))))
          .reset_index())
    s = s.nlargest(k, "vols") if order == "top" else s.nsmallest(k, "vols")
    s = s.merge(planes[["tailnum", "manufacturer", "model"]], on="tailnum", how="left")
    return pd.DataFrame({"Immatriculation": s.tailnum, "Compagnie": s.compagnie, "Vols": s.vols.map(fmt_int),
                         "Constructeur": s.manufacturer.fillna("inconnu (absent du registre FAA)"), "Modèle": s.model})


def planes_single_flight(f) -> int:
    counts = f.tailnum.value_counts()
    return int((counts == 1).sum())


def dest_per_carrier_figure(f):
    d = f.groupby("carrier_name").dest.nunique().sort_values()
    fig = go.Figure(go.Bar(x=d.values, y=d.index, orientation="h", marker_color=NEUTRAL_COLOR,
                           text=d.values, textposition="outside",
                           hovertemplate="%{y} : %{x} destinations<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Nombre de destinations"), height=640)
    return style(fig)


def dest_per_carrier_origin_figure(f):
    d = f.groupby(["carrier_name", "origin"]).dest.nunique().reset_index()
    # Plotly place la première catégorie en bas : on trie par total croissant pour avoir le plus grand en haut.
    order = list(d.groupby("carrier_name").dest.sum().sort_values().index)
    fig = go.Figure()
    for origin in sorted(d.origin.unique()):
        sub = d[d.origin == origin]
        fig.add_bar(y=sub.carrier_name, x=sub.dest, name=origin, orientation="h",
                    marker_color=ORIGIN_COLORS.get(origin),
                    hovertemplate=f"%{{y}} depuis {origin} : %{{x}} destinations<extra></extra>")
    style(fig)
    fig.update_layout(barmode="group", height=640, legend=dict(orientation="h", y=1.06, x=0),
                      margin=dict(t=50),
                      yaxis=dict(categoryorder="array", categoryarray=order),
                      xaxis=dict(title="Nombre de destinations"))
    return fig


def q4_stats(f) -> dict:
    hou = f[f.dest.isin(["IAH", "HOU"])]
    sea = f[f.dest == "SEA"]
    return {
        "houston": len(hou),
        "houston_detail": " · ".join(f"{k} : {fmt_int(v)}" for k, v in hou.dest.value_counts().items()),
        "seattle": len(sea),
        "sea_carriers": sea.carrier.nunique(),
        "sea_carrier_names": ", ".join(sorted(sea.carrier_name.unique())),
        "sea_planes": sea.tailnum.dropna().nunique(),
    }


def houston_table(f) -> pd.DataFrame:
    d = f[f.dest.isin(["IAH", "HOU"])].sort_values(["date", "sched_dep_time"])
    return pd.DataFrame({"Date": d.date.dt.strftime("%d/%m/%Y"), "Départ prévu": d.sched_dep_time,
                         "Compagnie": d.carrier_name, "Vol": d.flight, "Origine": d.origin,
                         "Destination": d.dest_name + " (" + d.dest + ")", "Avion": d.tailnum})


def flights_per_dest_table(f) -> pd.DataFrame:
    d = f.groupby(["dest", "dest_name"]).size().rename("n").reset_index().sort_values("n", ascending=False)
    return pd.DataFrame({"Code": d.dest, "Destination": d.dest_name, "Vols": d.n.map(fmt_int),
                         "% des vols": (d.n / len(f)).map(lambda x: fmt_pct(x, 2))})


def sorted_flights_table(f, airports, n: int = PREVIEW_ROWS) -> pd.DataFrame:
    names = airports.set_index("faa").name
    d = (f.assign(origin_name=f.origin.map(names))
          .sort_values(["dest_name", "origin_name", "carrier_name", "date", "sched_dep_time"]).head(n))
    return pd.DataFrame({"Destination": d.dest_name + " (" + d.dest + ")",
                         "Origine": d.origin_name + " (" + d.origin + ")", "Compagnie": d.carrier_name,
                         "Vol": d.flight, "Date": d.date.dt.strftime("%d/%m/%Y")})


def carriers_not_all_origins(f) -> pd.DataFrame:
    all_origins = set(f.origin.unique())
    g = f.groupby("carrier_name").origin.agg(lambda s: set(s.unique()))
    g = g[g.apply(len) < len(all_origins)]
    return pd.DataFrame({"Compagnie": g.index, "Dessert": g.map(lambda s: ", ".join(sorted(s))).values,
                         "Ne dessert pas": g.map(lambda s: ", ".join(sorted(all_origins - s))).values})


def carriers_all_dest(f) -> tuple[list[str], str, int, int]:
    n_dest = f.dest.nunique()
    per = f.groupby("carrier_name").dest.nunique()
    return list(per[per == n_dest].index), per.idxmax(), int(per.max()), n_dest


def synthesis_table(f, airports) -> pd.DataFrame:
    names = airports.set_index("faa").name
    d = (f.groupby(["origin", "dest", "dest_name", "carrier_name"]).size().rename("n").reset_index()
          .sort_values(["origin", "dest", "carrier_name"]))
    return pd.DataFrame({"Origine": d.origin + " – " + d.origin.map(names),
                         "Destination": d.dest + " – " + d.dest_name, "Compagnie": d.carrier_name, "Vols": d.n})


def exclusive_destinations(f) -> pd.DataFrame:
    n = f.groupby("dest").carrier.nunique()
    excl = n[n == 1].index
    d = (f[f.dest.isin(excl)].groupby(["dest", "dest_name", "carrier_name"]).size().rename("n").reset_index()
          .sort_values(["carrier_name", "dest"]))
    return pd.DataFrame({"Code": d.dest, "Destination": d.dest_name, "Compagnie exclusive": d.carrier_name,
                         "Vols": d.n.map(fmt_int)})


def majors_table(f) -> pd.DataFrame:
    sub = f[f.carrier.isin(list(MAJORS))]
    d = sub.carrier_name.value_counts()
    out = pd.DataFrame({"Compagnie": d.index, "Vols": d.map(fmt_int).values,
                        "% des vols de la base": [fmt_pct(x, 1) for x in d.values / len(f)]})
    total = pd.DataFrame([{"Compagnie": "Total United + American + Delta", "Vols": fmt_int(len(sub)),
                           "% des vols de la base": fmt_pct(len(sub) / len(f), 1)}])
    return pd.concat([out, total], ignore_index=True)


def majors_preview(f, n: int = PREVIEW_ROWS) -> pd.DataFrame:
    d = f[f.carrier.isin(list(MAJORS))].sort_values(["date", "sched_dep_time"]).head(n)
    return pd.DataFrame({"Date": d.date.dt.strftime("%d/%m/%Y"), "Départ réel": d.dep_time,
                         "Compagnie": d.carrier_name, "Vol": d.flight, "Origine": d.origin, "Destination": d.dest})


# ---------------------------------------------------------------- interface

def _question(text: str):
    return ui.p(ui.em(text), class_="text-muted")


def _card(title: str, *body):
    return ui.card(ui.card_header(title), *body)


@module.ui
def mission1_ui(app):
    f, airports, planes = app["flights"], app["airports"], app["raw"]["planes"]
    q4 = q4_stats(f)
    all_dest, best, best_n, n_dest = carriers_all_dest(f)
    excl = exclusive_destinations(f)

    return ui.TagList(
        ui.p("Réponses du notebook Mission1_Exploration.ipynb, recalculées sur la base Supabase. "
             "Cet onglet ignore les filtres de la barre latérale.", class_="text-muted small"),
        ui.navset_card_underline(
            ui.nav_panel(
                "Q1 · Chiffres clés",
                _question("Combien y a-t-il d'aéroports (en tout, de départ, de destination), d'aéroports sans "
                          "heure d'été, de fuseaux horaires, de compagnies, d'avions, de vols annulés ?"),
                html_table(q1_table(app)),
            ),
            ui.nav_panel(
                "Q2 · Les plus / moins prisés",
                _question("Aéroport de départ le plus emprunté ? 10 destinations les plus (moins) prisées, avec "
                          "nom complet et % ? 10 avions qui ont le plus (moins) décollé ?"),
                _card("Aéroports de départ", html_table(origins_table(f, airports))),
                ui.layout_columns(
                    _card("10 destinations les plus prisées", html_table(destinations_table(f, "top"))),
                    _card("10 destinations les moins prisées", html_table(destinations_table(f, "bottom"))),
                ),
                ui.layout_columns(
                    _card("10 avions qui ont le plus décollé", html_table(planes_table(f, planes, "top"))),
                    _card("10 avions qui ont le moins décollé",
                          html_table(planes_table(f, planes, "bottom")),
                          ui.p(f"{fmt_int(planes_single_flight(f))} avions n'ont décollé qu'une seule fois : "
                               "les 10 affichés en sont un échantillon.", class_="text-muted small mt-2")),
                ),
            ),
            ui.nav_panel(
                "Q3 · Destinations par compagnie",
                _question("Combien chaque compagnie a desservi de destinations ; et par aéroport d'origine ?"),
                ui.layout_columns(
                    _card("Destinations desservies par compagnie", output_widget("q3_carrier")),
                    _card("Par compagnie et aéroport d'origine", output_widget("q3_origin")),
                ),
            ),
            ui.nav_panel(
                "Q4 · Houston & Seattle",
                _question("Tous les vols ayant atterri à Houston (IAH ou HOU) ? Combien de vols de NYC vers Seattle, "
                          "combien de compagnies desservent cette destination et combien d'avions uniques ?"),
                ui.layout_column_wrap(
                    ui.value_box("Vols vers Houston", fmt_int(q4["houston"]), q4["houston_detail"]),
                    ui.value_box("Vols NYC → Seattle", fmt_int(q4["seattle"])),
                    ui.value_box("Compagnies vers Seattle", str(q4["sea_carriers"]), q4["sea_carrier_names"]),
                    ui.value_box("Avions uniques vers Seattle", fmt_int(q4["sea_planes"])),
                    width="230px", fill=False,
                ),
                _card("Les vols ayant atterri à Houston", ui.output_data_frame("q4_houston")),
            ),
            ui.nav_panel(
                "Q5 · Vols par destination",
                _question("Nombre de vols par destination ? Trier les vols par destination, aéroport d'origine et "
                          "compagnie (ordre alphabétique, avec les noms explicites) ?"),
                ui.layout_columns(
                    _card("Vols par destination", html_table(flights_per_dest_table(f), max_height=520)),
                    _card(f"Vols triés : destination → origine → compagnie "
                          f"({fmt_int(PREVIEW_ROWS)} premiers sur {fmt_int(len(f))})",
                          ui.output_data_frame("q5_sorted")),
                    col_widths=(5, 7),
                ),
            ),
            ui.nav_panel(
                "Q6 · Couverture des compagnies",
                _question("Compagnies qui n'opèrent pas sur tous les aéroports d'origine ? Compagnies qui desservent "
                          "toutes les destinations ? Tableau des origines et destinations de chaque compagnie."),
                ui.layout_columns(
                    _card("Compagnies absentes d'au moins un aéroport de départ",
                          html_table(carriers_not_all_origins(f))),
                    _card("Compagnies desservant toutes les destinations",
                          ui.p(", ".join(all_dest) if all_dest else
                               f"Aucune compagnie ne dessert à elle seule les {n_dest} destinations."),
                          ui.p(f"Celle qui en dessert le plus : {best}, avec {best_n} destinations "
                               f"({fmt_pct(best_n / n_dest, 0)}).", class_="text-muted")),
                ),
                _card("Origines et destinations de chaque compagnie (filtrable)", ui.output_data_frame("q6_synth")),
            ),
            ui.nav_panel(
                "Q7 · Destinations exclusives",
                _question("Quelles sont les destinations exclusives à certaines compagnies ?"),
                _card(f"{len(excl)} destinations desservies par une seule compagnie",
                      html_table(excl, max_height=600)),
            ),
            ui.nav_panel(
                "Q8 · United, American, Delta",
                _question("Filtrer les vols exploités par United, American ou Delta ?"),
                _card("Nombre de vols", html_table(majors_table(f))),
                _card(f"Aperçu des vols filtrés ({fmt_int(PREVIEW_ROWS)} premiers)", ui.output_data_frame("q8_preview")),
            ),
        ),
    )


@module.server
def mission1_server(input, output, session, app):
    f, airports = app["flights"], app["airports"]

    @render_plotly
    def q3_carrier():
        return dest_per_carrier_figure(f)

    @render_plotly
    def q3_origin():
        return dest_per_carrier_origin_figure(f)

    @render.data_frame
    def q4_houston():
        return render.DataGrid(houston_table(f), filters=True, height="420px")

    @render.data_frame
    def q5_sorted():
        return render.DataGrid(sorted_flights_table(f, airports), filters=True, height="520px")

    @render.data_frame
    def q6_synth():
        return render.DataGrid(synthesis_table(f, airports), filters=True, height="480px")

    @render.data_frame
    def q8_preview():
        return render.DataGrid(majors_preview(f), filters=True, height="420px")
