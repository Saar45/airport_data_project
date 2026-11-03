"""Accès aux données : Supabase (Postgres) ou données locales nycflights13.

Choix via la variable d'environnement DATA_SOURCE ("supabase" ou "local").
Les données sont historiques : elles sont mises en cache sur disque
(app/cache/<source>.pkl) pour que l'app démarre vite le jour J.
Forcer un rechargement : REFRESH_CACHE=true, ou supprimer app/cache/.
"""

import os
import pickle
from decimal import Decimal
from pathlib import Path

import pandas as pd

from data_prep import prepare_data
from model import fit_problem_model

TABLES = ["flights", "airports", "airlines", "planes", "weather"]
CACHE_DIR = Path(__file__).parent / "cache"
# À incrémenter quand la structure du dictionnaire APP change : un cache plus ancien est alors reconstruit.
CACHE_VERSION = 2


def make_engine():
    from sqlalchemy import URL, create_engine

    required = ["SUPABASE_HOST", "SUPABASE_USER", "SUPABASE_PASSWORD"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"Variables d'environnement manquantes : {', '.join(missing)}. "
            "Copier .env.example vers .env et le compléter."
        )
    url = URL.create(
        "postgresql+psycopg",
        username=os.environ["SUPABASE_USER"],
        password=os.environ["SUPABASE_PASSWORD"],
        host=os.environ["SUPABASE_HOST"],              
        port=int(os.getenv("SUPABASE_PORT", "5432")),
        database=os.getenv("SUPABASE_DB", "postgres"),
    )
    return create_engine(url, connect_args={"sslmode": "require"})


def _decimals_to_float(df: pd.DataFrame) -> pd.DataFrame:
    """Les colonnes Postgres NUMERIC arrivent en Decimal (dtype object) : on les convertit."""
    for col in df.columns:
        if not pd.api.types.is_object_dtype(df[col]):
            continue
        first = df[col].dropna().head(1)
        if len(first) and isinstance(first.iloc[0], Decimal):
            df[col] = pd.to_numeric(df[col])
    return df


def read_supabase() -> dict[str, pd.DataFrame]:
    engine = make_engine()
    schema = os.getenv("SUPABASE_SCHEMA", "public")
    try:
        with engine.connect() as con:
            return {t: _decimals_to_float(pd.read_sql_table(t, con, schema=schema)) for t in TABLES}
    finally:
        engine.dispose()


def read_supabase_meta() -> dict:
    """Structure de la base telle que la voit l'app : lignes, droits, RLS, contraintes (onglet Mission 2)."""
    from datetime import datetime

    from sqlalchemy import text

    engine = make_engine()
    schema = os.getenv("SUPABASE_SCHEMA", "public")
    try:
        with engine.connect() as con:
            def q(sql, **params):
                return con.execute(text(sql), params).fetchall()

            tables = []
            for t in TABLES:
                full = f"{schema}.{t}"
                privileges = {p: q("select has_table_privilege(:t, :p)", t=full, p=p)[0][0]
                              for p in ("SELECT", "INSERT", "UPDATE", "DELETE")}
                rls = q("""select c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace
                           where n.nspname = :s and c.relname = :t""", s=schema, t=t)
                tables.append({
                    "table": t,
                    "rows": q(f'select count(*) from "{schema}"."{t}"')[0][0],
                    "rls": bool(rls and rls[0][0]),
                    "policies": [r[0] for r in q("select policyname from pg_policies where schemaname = :s and tablename = :t",
                                                 s=schema, t=t)],
                    "privileges": privileges,
                })
            constraints = [
                {"table": r[0].split(".")[-1], "name": r[1], "type": {"p": "PK", "u": "UNIQUE", "f": "FK"}[r[2]],
                 "definition": r[3], "validated": r[4]}
                for r in q("""select cast(conrelid as regclass)::text, conname, contype,
                                     pg_get_constraintdef(oid), convalidated
                              from pg_constraint
                              where connamespace = cast(:s as regnamespace) and contype in ('p', 'u', 'f')
                              order by 1, 3, 2""", s=schema)
            ]
            user = q("select current_user")[0][0]
    finally:
        engine.dispose()
    return {"user": user, "schema": schema, "tables": tables, "constraints": constraints,
            "read_at": datetime.now().strftime("%d/%m/%Y %H:%M")}


def read_local() -> dict[str, pd.DataFrame]:
    # On lit directement les CSV du package : son __init__ importe pkg_resources,
    # absent des versions récentes de setuptools.
    import importlib.util

    spec = importlib.util.find_spec("nycflights13")
    if spec is None:
        raise RuntimeError("Le package nycflights13 est requis pour DATA_SOURCE=local.")
    data_dir = Path(spec.submodule_search_locations[0]) / "data"
    files = {t: data_dir / f"{t}.csv" for t in TABLES} | {"flights": data_dir / "flights.csv.zip"}
    return {t: pd.read_csv(p) for t, p in files.items()}


def load_app_data(source: str | None = None, refresh: bool = False) -> dict:
    source = source or os.getenv("DATA_SOURCE", "local")
    if source not in ("local", "supabase"):
        raise ValueError(f"DATA_SOURCE inconnu : {source!r} (attendu : local ou supabase)")

    cache_file = CACHE_DIR / f"{source}.pkl"
    if not refresh and cache_file.exists():
        with cache_file.open("rb") as f:
            cached = pickle.load(f)
        if cached.get("cache_version") == CACHE_VERSION:
            print(f"Chargement du cache : {cache_file}")
            return cached
        print("Cache d'une ancienne version de l'app : reconstruction.")

    print(f"Lecture des données depuis : {source}")
    raw = read_supabase() if source == "supabase" else read_local()
    empty = [t for t, df in raw.items() if df.empty]
    if empty:
        # On refuse de mettre en cache une base vide (tables non chargées, ou RLS
        # sans policy SELECT pour le rôle de l'app : les lignes sont alors invisibles).
        raise RuntimeError(f"Tables vides côté {source} : {', '.join(empty)}. "
                           "Données non importées, ou RLS sans policy de lecture pour ce rôle.")
    data = prepare_data(raw)
    data["model"] = fit_problem_model(data["flights"])
    data["source"] = source
    data["db_meta"] = read_supabase_meta() if source == "supabase" else None
    data["cache_version"] = CACHE_VERSION

    try:
        CACHE_DIR.mkdir(exist_ok=True)
        with cache_file.open("wb") as f:
            pickle.dump(data, f)
    except OSError as e:
        # Hébergeur en lecture seule : l'app fonctionne sans cache (rechargement à chaque démarrage).
        print(f"Cache non enregistré ({e}).")
    return data
