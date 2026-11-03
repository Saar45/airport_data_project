"""Nettoyage, jointures et indicateurs dérivés. Exécuté une seule fois (puis mis en cache)."""

import numpy as np
import pandas as pd

from utils import JOURS

# Aéroports présents dans flights.dest mais absents de la table airports (cf. énoncé).
MISSING_AIRPORTS = pd.DataFrame({
    "faa": ["BQN", "PSE", "SJU", "STT"],
    "name": ["Rafael Hernandez Airport", "Mercedita Airport", "San Juan Airport", "Cyril E. King Airport"],
    "lat": [18.4949, 18.0083, 18.4394, 18.3373],
    "lon": [-67.1294, -66.5630, -66.0018, -64.9734],
    "tzone": ["America/Puerto_Rico"] * 3 + ["America/St_Thomas"],
})

WEATHER_KEY = ["origin", "year", "month", "day", "hour"]


def prepare_data(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    raw = {k: v.rename(columns=str.lower) for k, v in raw.items()}

    airports = pd.concat(
        [raw["airports"], MISSING_AIRPORTS[~MISSING_AIRPORTS.faa.isin(raw["airports"].faa)]],
        ignore_index=True,
    )

    # Dédoublonnage de la clé météo : nycflights13 contient quelques doublons
    # au changement d'heure, qui dupliqueraient des vols lors de la jointure.
    weather = raw["weather"].drop_duplicates(WEATHER_KEY)[WEATHER_KEY + ["temp", "wind_speed", "precip", "visib"]]

    planes = raw["planes"][["tailnum", "year", "manufacturer", "model", "seats"]].rename(columns={"year": "plane_year"})
    m = planes.manufacturer.fillna("")
    planes["manufacturer"] = np.select(
        [m.str.contains("AIRBUS"), m.str.contains("MCDONNELL")],
        ["AIRBUS", "MCDONNELL DOUGLAS"],
        default=planes.manufacturer,
    )

    f = raw["flights"].copy()
    f["date"] = pd.to_datetime(f[["year", "month", "day"]])
    f["wday"] = pd.Categorical.from_codes(f.date.dt.day_of_week, categories=JOURS, ordered=True)
    # Un vol annulé n'a pas d'heure de départ réelle ; un vol parti sans retard
    # à l'arrivée connu est considéré comme dérouté.
    f["cancelled"] = f.dep_time.isna()
    f["flown"] = ~f.cancelled
    f["diverted"] = f.flown & f.arr_delay.isna()
    f["delayed"] = f.flown & ~f.diverted & (f.arr_delay > 15)
    f["problem"] = f.cancelled | f.diverted | f.delayed

    f = (
        f.merge(raw["airlines"][["carrier", "name"]].rename(columns={"name": "carrier_name"}),
                on="carrier", how="left", validate="many_to_one")
         .merge(airports[["faa", "name"]].rename(columns={"faa": "dest", "name": "dest_name"}),
                on="dest", how="left", validate="many_to_one")
         .merge(weather, on=WEATHER_KEY, how="left", validate="many_to_one")
         .merge(planes, on="tailnum", how="left", validate="many_to_one")
    )
    f["carrier_name"] = f.carrier_name.fillna(f.carrier)
    f["dest_name"] = f.dest_name.fillna(f.dest)
    f["plane_known"] = f.plane_year.notna() | f.manufacturer.notna()
    f["plane_age"] = f.year - f.plane_year

    return {
        "flights": f,
        "airports": airports,
        "airlines": raw["airlines"],
        # Tables telles que lues dans la base, sans correction : réponses de la Mission 1
        # et contrôles qualité de la Mission 2 (flights brut = colonnes d'origine de `flights`).
        "raw": {t: raw[t] for t in ("airports", "airlines", "planes", "weather")},
    }
