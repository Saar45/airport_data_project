"""Point d'entrée de l'application. Lancer : uv run shiny run app/app.py --reload"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from shiny import App, reactive, ui

# Les modules de l'app (data_source, modules/...) sont importés sans préfixe : on s'assure que
# ce dossier est dans le chemin, quel que soit le serveur qui lance l'app (shiny run, Connect Cloud).
sys.path.insert(0, str(Path(__file__).parent))
# En local, les secrets viennent du .env à la racine. Sur Connect Cloud, des « Variables » de l'app.
load_dotenv(Path(__file__).parent.parent / ".env")

from data_source import load_app_data  # noqa: E402
from modules.carriers import carriers_server, carriers_ui  # noqa: E402
from modules.map import map_server, map_ui  # noqa: E402
from modules.mission1 import mission1_server, mission1_ui  # noqa: E402
from modules.mission2 import mission2_server, mission2_ui  # noqa: E402
from modules.overview import overview_server, overview_ui  # noqa: E402
from modules.planes import planes_server, planes_ui  # noqa: E402
from modules.predict import predict_server, predict_ui  # noqa: E402
from modules.temporal import temporal_server, temporal_ui  # noqa: E402
from modules.weather import weather_server, weather_ui  # noqa: E402

# Chargé une seule fois au démarrage, partagé entre toutes les sessions.
APP = load_app_data(refresh=os.getenv("REFRESH_CACHE") == "true")

airlines = APP["airlines"].sort_values("name")
carrier_choices = {c: f"{n} ({c})" for c, n in zip(airlines.carrier, airlines.name)}
origin_choices = sorted(APP["flights"].origin.unique())
# Toutes les destinations desservies, y compris celles ajoutées par data_prep (SJU, BQN, STT, PSE).
dests = APP["flights"][["dest", "dest_name"]].drop_duplicates("dest").sort_values("dest_name")
dest_choices = {d: f"{n} ({d})" for d, n in zip(dests.dest, dests.dest_name)}

app_ui = ui.page_navbar(
    ui.nav_panel("Vue d'ensemble", overview_ui("overview")),
    ui.nav_panel("Mission 1", mission1_ui("mission1", APP)),
    ui.nav_panel("Mission 2", mission2_ui("mission2", APP)),
    ui.nav_panel("Quand ?", temporal_ui("temporal")),
    ui.nav_panel("Compagnies & routes", carriers_ui("carriers")),
    ui.nav_panel("Météo", weather_ui("weather")),
    ui.nav_panel("Avions", planes_ui("planes")),
    ui.nav_panel("Carte", map_ui("map")),
    ui.nav_panel("Prédiction", predict_ui("predict", APP["model"], carrier_choices)),
    ui.nav_spacer(),
    ui.nav_control(ui.span(f"Source : {APP['source']}", class_="badge bg-secondary")),
    title="Trafic aérien NYC",
    sidebar=ui.sidebar(
        ui.input_checkbox_group("origin", "Aéroport d'origine", origin_choices, selected=origin_choices),
        ui.input_selectize("carrier", "Compagnies", carrier_choices, multiple=True,
                           options={"placeholder": "Toutes"}),
        ui.input_selectize("dest", "Destinations", dest_choices, multiple=True,
                           options={"placeholder": "Toutes"}),
        ui.input_slider("months", "Mois", 1, 12, (1, 12), step=1),
        ui.p("Les filtres s'appliquent aux onglets d'analyse, pas aux onglets Mission 1, Mission 2 et Prédiction.",
             class_="text-muted small"),
        title="Filtres",
    ),
    fillable=False,
)


def server(input, output, session):
    # Filtre vide = pas de filtre.
    @reactive.calc
    def flights():
        df = APP["flights"]
        if input.origin():
            df = df[df.origin.isin(input.origin())]
        if input.carrier():
            df = df[df.carrier.isin(input.carrier())]
        if input.dest():
            df = df[df.dest.isin(input.dest())]
        lo, hi = input.months()
        return df[df.month.between(lo, hi)]

    overview_server("overview", flights)
    mission1_server("mission1", APP)
    mission2_server("mission2")
    temporal_server("temporal", flights)
    carriers_server("carriers", flights)
    weather_server("weather", flights)
    planes_server("planes", flights)
    map_server("map", flights, APP["airports"])
    predict_server("predict", APP["model"])


app = App(app_ui, server)
