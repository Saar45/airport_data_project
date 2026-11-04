"""Tests de l'application : données, graphiques, modèle, onglets Mission 1 / 2 et démarrage de l'app."""

import math

import pandas as pd
import pytest
from starlette.testclient import TestClient

from model import predict_problem
from modules import carriers, map as map_tab, mission1, mission2, overview, planes, predict, temporal, weather
from utils import fmt_int, fmt_min, fmt_pct, kpis, summarise


# ---------------------------------------------------------------- données

def test_prepared_flights(app_data):
    f = app_data["flights"]
    assert len(f) > 0
    # Les jointures ne doivent jamais dupliquer de vols (ex. doublons de la table weather).
    assert not f.duplicated(["year", "month", "day", "sched_dep_time", "carrier", "flight", "origin"]).any()
    # Définition d'un « problème » : retard > 15 min, annulation ou déroutement.
    assert (f.problem == (f.cancelled | f.diverted | f.delayed)).all()
    assert not (f.cancelled & f.delayed).any()
    assert f.dest_name.notna().all() and f.carrier_name.notna().all()


def test_missing_airports_added(app_data):
    assert {"BQN", "PSE", "SJU", "STT"} <= set(app_data["airports"].faa)


def test_raw_tables_kept(app_data):
    assert set(app_data["raw"]) == {"airports", "airlines", "planes", "weather"}
    assert app_data["db_meta"] is None          # mode local : pas de lecture de la base


# ---------------------------------------------------------------- graphiques et tableaux

SUBSETS = {
    "toutes": lambda f: f,
    "JFK seul": lambda f: f[f.origin == "JFK"],
    "une destination": lambda f: f[f.dest == "SJU"],
    "sélection vide": lambda f: f.iloc[0:0],
}


@pytest.mark.parametrize("subset", SUBSETS)
def test_every_chart_and_table_builds(app_data, subset):
    f = SUBSETS[subset](app_data["flights"])
    kpis(f)
    overview.monthly_figure(f)
    temporal.heatmap_figure(f)
    daily = summarise(f, "date")
    temporal.daily_figure(daily)
    temporal.worst_days_table(daily)
    carriers.carriers_figure(f)
    carriers.routes_table(f)
    for var in weather.WEATHER_VARS:
        weather.weather_figure(f, var)
        assert weather.coverage_text(f, var)
    planes.age_figure(f)
    planes.manufacturer_figure(f)
    map_tab.map_figure(f, app_data["airports"])


def test_summarise_rates(app_data):
    s = summarise(app_data["flights"], "origin")
    assert set(s.origin) == {"EWR", "JFK", "LGA"}
    for col in ("problem_rate", "cancel_rate", "delay_rate"):
        assert s[col].between(0, 1).all()


def test_kpis_empty_selection():
    empty = pd.DataFrame(columns=["problem", "cancelled", "arr_delay", "delayed", "flown"])
    k = kpis(empty)
    assert k["n"] == 0 and math.isnan(k["problem_rate"])


# ---------------------------------------------------------------- modèle

def test_model_predicts_probabilities(app_data):
    model = app_data["model"]
    assert model["auc"] > 0.6
    assert set(model["levels"]["origin"]) == {"EWR", "JFK", "LGA"}
    scenario = pd.DataFrame([{"carrier": c, "origin": "JFK", "month": "7", "hour": 18,
                              "visib": 10, "wind_speed": 10, "precip": 0} for c in model["levels"]["carrier"]])
    p = predict_problem(model, scenario)
    assert ((p >= 0) & (p <= 1)).all()
    predict.hourly_figure(model, scenario.head(1), 18)


def test_bad_weather_increases_risk(app_data):
    model = app_data["model"]
    good = pd.DataFrame([{"carrier": "UA", "origin": "EWR", "month": "1", "hour": 18,
                          "visib": 10, "wind_speed": 5, "precip": 0}])
    bad = good.assign(visib=0.5, wind_speed=30, precip=0.3)
    assert predict_problem(model, bad)[0] > predict_problem(model, good)[0]


# ---------------------------------------------------------------- Mission 1

def test_mission1_answers(app_data):
    f, airports = app_data["flights"], app_data["airports"]
    q1 = mission1.q1_table(app_data)
    assert len(q1) == 8
    assert mission1.q4_stats(f)["houston"] == f.dest.isin(["IAH", "HOU"]).sum()
    assert len(mission1.destinations_table(f, "top")) == 10
    assert len(mission1.planes_table(f, app_data["raw"]["planes"], "bottom")) == 10
    assert len(mission1.sorted_flights_table(f, airports)) == mission1.PREVIEW_ROWS
    excl = mission1.exclusive_destinations(f)
    assert (f[f.dest.isin(excl.Code)].groupby("dest").carrier.nunique() == 1).all()
    majors = mission1.majors_table(f)
    assert majors.iloc[-1].Vols == fmt_int(f.carrier.isin(["UA", "AA", "DL"]).sum())
    mission1.dest_per_carrier_figure(f)
    mission1.dest_per_carrier_origin_figure(f)


# ---------------------------------------------------------------- Mission 2

def test_mission2_checks(app_data):
    checks = mission2.quality_checks(app_data)
    assert {c["status"] for c in checks} <= {"ok", "warn", "ko"}
    by_name = {c["ctrl"]: c for c in checks}
    # Données locales brutes : les 4 aéroports manquants doivent être détectés (problème de l'énoncé).
    dest = by_name["flights.dest → airports"]
    assert dest["status"] == "ko" and "SJU" in dest["result"]
    assert by_name["flights.tailnum → planes"]["status"] == "warn"
    table = mission2.relations_table(app_data, checks)
    assert (table["Déclarée en base (FK)"].iloc[:-1] == "non lu (mode local)").all()


def test_added_planes_recognised(app_data):
    """Comme en base : les avions absents du registre sont ajoutés dans planes avec seulement l'immatriculation.
    Les réponses doivent toujours citer le fichier fourni, et le contrôle ne doit pas masquer le problème."""
    planes = app_data["raw"]["planes"]
    missing = sorted(set(app_data["flights"].tailnum.dropna()) - set(planes.tailnum))
    with_stubs = pd.concat([planes, pd.DataFrame({"tailnum": missing})], ignore_index=True)
    app = {**app_data, "raw": {**app_data["raw"], "planes": with_stubs}}

    q1 = mission1.q1_table(app).set_index("Indicateur")
    assert q1.loc["Avions (table planes)", "Valeur"] == fmt_int(len(with_stubs))
    assert f"{fmt_int(len(planes))} dans le fichier fourni" in q1.loc["Avions (table planes)", "Détail"]

    checks = {c["ctrl"]: c for c in mission2.quality_checks(app)}
    tailnum = checks["flights.tailnum → planes"]
    assert tailnum["status"] == "warn" and tailnum["respected"] == "oui"
    assert "Clé étrangère respectée" in tailnum["result"] and fmt_int(len(missing)) in tailnum["result"]


# ---------------------------------------------------------------- formatage

def test_french_formatting():
    assert fmt_pct(0.2589) == "25,9 %"
    assert fmt_pct(float("nan")) == "–"
    assert fmt_int(252704) == "252 704"
    assert fmt_min(-0.04) == "0,0 min"          # jamais « -0,0 »
    assert fmt_min(6.94) == "6,9 min"


# ---------------------------------------------------------------- application complète

def test_app_homepage(shiny_app):
    with TestClient(shiny_app) as client:
        response = client.get("/")
    assert response.status_code == 200
    for text in ("Trafic aérien NYC", "Mission 1", "Mission 2", "Prédiction", "Source : local"):
        assert text in response.text
