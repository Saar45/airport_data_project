"""Modèle de démonstration : P(problème) = P(retard > 15 min, annulation ou déroutement).

Régression logistique volontairement simple, à améliorer (variables, interactions,
autres modèles, calibration...).
"""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CAT = ["carrier", "origin", "month"]
NUM = ["hour", "visib", "wind_speed", "precip"]
WEATHER = ["visib", "wind_speed", "precip"]


def _features(df: pd.DataFrame) -> pd.DataFrame:
    X = df[CAT + NUM].copy()
    X["month"] = X["month"].astype(int).astype(str)
    return X


def fit_problem_model(flights: pd.DataFrame, n_max: int = 50_000, seed: int = 2013) -> dict:
    # On garde aussi les vols sans météo (la table weather peut être partielle) :
    # sinon le modèle ne connaîtrait que les aéroports/mois couverts par la météo.
    data = flights.dropna(subset=CAT + ["hour"])
    data = data[~(data.wind_speed >= 100)]  # valeur aberrante connue (~1048 mph), les NaN sont conservés
    weather_coverage = float(data[WEATHER].notna().all(axis=1).mean())
    if len(data) > n_max:
        data = data.sample(n=n_max, random_state=seed)

    X, y = _features(data), data["problem"].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y)

    pipe = Pipeline([
        ("prep", ColumnTransformer([
            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT),
            # Météo manquante : remplacée par la médiane + colonne indicatrice « météo inconnue »,
            # pour que l'effet météo ne soit appris que sur les vols qui en ont une.
            ("num", Pipeline([
                ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                ("scale", StandardScaler()),
            ]), NUM),
        ])),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    pipe.fit(X_train, y_train)

    return {
        "pipeline": pipe,
        "base_rate": float(y.mean()),
        "auc": float(roc_auc_score(y_test, pipe.predict_proba(X_test)[:, 1])),
        "weather_coverage": weather_coverage,
        "levels": {
            "carrier": sorted(X.carrier.unique()),
            "origin": sorted(X.origin.unique()),
            "month": sorted(X.month.unique(), key=int),
        },
    }


def predict_problem(model: dict, scenarios: pd.DataFrame):
    return model["pipeline"].predict_proba(_features(scenarios))[:, 1]
