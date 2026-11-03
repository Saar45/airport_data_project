"""Onglet Mission 2 : création de la base Supabase (notebook Colab), schéma, contrôles qualité, sécurité.

Les contrôles sont recalculés sur les données ; le schéma, les droits et la RLS viennent de
APP["db_meta"], lu dans Supabase au moment où le cache est construit.
"""

import html
import re

import pandas as pd
from shiny import module, ui

from data_prep import MISSING_AIRPORTS, WEATHER_KEY
from utils import MOIS, fmt_int, fmt_pct, html_table

COLAB_URL = "https://colab.research.google.com/drive/1kFgVOSJJK44semax7cZEpBHEDENG4vWq?usp=sharing"
ADDED_AIRPORTS = list(MISSING_AIRPORTS.faa)

SOURCES = pd.DataFrame([
    ("airlines.json", "JSON", "pd.read_json", "Fichier propre."),
    ("airports.xlsx", "Excel", "pd.read_excel", "Colonne d'index « Unnamed: 0 » supprimée."),
    ("flights.xlsx", "Excel, une seule colonne", "pd.read_excel puis pd.read_csv",
     "Chaque ligne est un CSV complet dans une seule cellule : le texte est reconstruit puis relu en CSV."),
    ("planes.html", "Page HTML", "pd.read_html(...)[0]", "Colonne d'index supprimée."),
    ("weather.pdf", "PDF", "pdftotext -layout puis pd.read_csv",
     "Lignes vides et en-têtes répétés à chaque page filtrés (on garde les lignes à 14 virgules)."),
], columns=["Fichier", "Format", "Lecture", "Nettoyage"])

# Relations attendues par l'énoncé : (libellé, table enfant, colonnes, table parente, cardinalité)
RELATIONS = [
    ("flights.carrier → airlines.carrier", "flights", "carrier", "airlines", "N–1 : une compagnie, plusieurs vols"),
    ("flights.origin → airports.faa", "flights", "origin", "airports", "N–1"),
    ("flights.dest → airports.faa", "flights", "dest", "airports", "N–1"),
    ("flights.tailnum → planes.tailnum", "flights", "tailnum", "planes", "N–1 : un avion, plusieurs vols"),
    ("weather.origin → airports.faa", "weather", "origin", "airports", "N–1"),
    ("flights → weather (origin, year, month, day, hour)", "flights", "origin, year, month, day, hour", "weather",
     "N–1 : une observation horaire, plusieurs vols"),
]

BADGES = {"ok": ("success", "OK"), "warn": ("warning", "À noter"), "ko": ("danger", "Problème")}


# ---------------------------------------------------------------- contrôles (fonctions pures)

def _missing(child: pd.Series, parent: pd.Series) -> pd.Series:
    s = child.dropna()
    return s[~s.isin(set(parent.dropna()))]


def _months(series) -> str:
    m = sorted(int(x) for x in series.unique())
    return f"{MOIS[m[0] - 1]}–{MOIS[m[-1] - 1]}" if m else "–"


def weather_match(app) -> pd.Series:
    """Pour chaque vol : existe-t-il une ligne météo (même aéroport, date et heure) ?"""
    f, w = app["flights"], app["raw"]["weather"]
    keys = pd.MultiIndex.from_frame(w[WEATHER_KEY])
    return pd.Series(pd.MultiIndex.from_frame(f[WEATHER_KEY]).isin(keys), index=f.index)


def quality_checks(app) -> list[dict]:
    f, r = app["flights"], app["raw"]
    ap, al, pl, w = r["airports"], r["airlines"], r["planes"], r["weather"]
    out = []

    def add(cat, ctrl, status, result):
        out.append({"cat": cat, "ctrl": ctrl, "status": status, "result": result})

    # Clés étrangères
    for col, parent, label in [("carrier", al.carrier, "flights.carrier → airlines"),
                               ("origin", ap.faa, "flights.origin → airports")]:
        miss = _missing(f[col], parent)
        add("Clés étrangères", label, "ok" if miss.empty else "ko",
            "Toutes les valeurs existent." if miss.empty
            else f"{miss.nunique()} codes absents ({fmt_int(len(miss))} vols) : {', '.join(sorted(miss.unique())[:8])}")

    miss = _missing(f.dest, ap.faa)
    added = sorted(ap.faa[ap.faa.isin(ADDED_AIRPORTS)])
    add("Clés étrangères", "flights.dest → airports", "ok" if miss.empty else "ko",
        (f"Toutes les destinations existent. Les {len(added)} aéroports absents du fichier fourni "
         f"({', '.join(added)}) ont été ajoutés en base." if added else "Toutes les destinations existent.")
        if miss.empty else
        f"{miss.nunique()} codes absents ({fmt_int(len(miss))} vols) : {', '.join(sorted(miss.unique()))}")

    miss = _missing(w.origin, ap.faa)
    add("Clés étrangères", "weather.origin → airports", "ok" if miss.empty else "ko",
        "Toutes les valeurs existent." if miss.empty else f"Codes absents : {', '.join(sorted(miss.unique()))}")

    miss = _missing(f.tailnum, pl.tailnum)
    if miss.empty:
        add("Clés étrangères", "flights.tailnum → planes", "ok", "Tous les avions existent.")
    else:
        by_carrier = f[f.tailnum.isin(set(miss))].carrier.value_counts()
        aa_mq = by_carrier.reindex(["AA", "MQ"]).fillna(0).sum() / by_carrier.sum()
        add("Clés étrangères", "flights.tailnum → planes", "warn",
            f"{fmt_int(miss.nunique())} avions absents de planes, soit {fmt_int(len(miss))} vols "
            f"({fmt_pct(len(miss) / len(f))}). {fmt_pct(aa_mq, 0)} chez AA et MQ, qui déclarent des numéros "
            "de flotte et non des immatriculations (problème annoncé par l'énoncé).")

    match = weather_match(app)
    matched = app["flights"][match]
    add("Clés étrangères", "flights → weather", "ok" if match.all() else "warn",
        f"{fmt_pct(match.mean())} des vols ont une observation météo correspondante"
        + (f" (aéroports : {', '.join(sorted(matched.origin.unique()))}, mois : {_months(matched.month)})."
           if len(matched) else "."))

    # Unicité des clés
    dups = {"airports.faa": ap.faa.duplicated().sum(), "airlines.carrier": al.carrier.duplicated().sum(),
            "planes.tailnum": pl.tailnum.duplicated().sum()}
    add("Unicité des clés", "Clés primaires des tables de référence", "ok" if not any(dups.values()) else "ko",
        " · ".join(f"{k} : {v} doublon(s)" for k, v in dups.items()))
    d = w.duplicated(WEATHER_KEY).sum()
    add("Unicité des clés", "weather (origin, year, month, day, hour)", "ok" if d == 0 else "ko",
        f"{d} doublon(s) : la clé composite est {'valide' if d == 0 else 'invalide'}.")
    flight_key = ["year", "month", "day", "hour", "carrier", "flight"]
    d = f.duplicated(flight_key).sum()
    add("Unicité des clés", "flights (year, month, day, hour, carrier, flight)", "ok" if d == 0 else "ko",
        f"{d} doublon(s). Le numéro de vol seul n'est pas une clé : "
        f"{fmt_int(f.flight.nunique())} numéros pour {fmt_int(len(f))} vols.")

    # Formats (expressions régulières)
    codes = pd.concat([ap.faa, f.origin, f.dest]).dropna().unique()
    bad = [c for c in codes if not re.fullmatch(r"[A-Z0-9]{3}", str(c))]
    add("Formats (regex)", "Codes aéroport ^[A-Z0-9]{3}$", "ok" if not bad else "ko",
        "Tous conformes." if not bad else f"Non conformes : {', '.join(bad[:8])}")
    carriers = pd.concat([al.carrier, f.carrier]).dropna().unique()
    bad = [c for c in carriers if not re.fullmatch(r"[A-Z0-9]{2}", str(c))]
    add("Formats (regex)", "Codes compagnie ^[A-Z0-9]{2}$", "ok" if not bad else "ko",
        "Tous conformes." if not bad else f"Non conformes : {', '.join(bad)}")
    tails = pd.concat([pl.tailnum, f.tailnum]).dropna()
    bad = tails[~tails.astype(str).str.fullmatch(r"N[0-9A-Z]{1,5}")].value_counts()
    add("Formats (regex)", "Immatriculations ^N[0-9A-Z]{1,5}$", "ok" if bad.empty else "warn",
        "Toutes conformes." if bad.empty else
        "Non conformes : " + ", ".join(f"« {k} » ({v} lignes)" for k, v in bad.head(5).items()))

    # Valeurs manquantes déguisées en texte
    fake = {}
    tables = {"airports": ap, "airlines": al, "planes": pl, "weather": w,
              "flights": f[["carrier", "tailnum", "origin", "dest"]]}
    for name, df in tables.items():
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
                values = df[col].dropna().astype(str).str.strip()     # les vrais NULL sont exclus
                n = values.isin(["", "\\N", "NA", "NaN", "nan", "None"]).sum()
                if n > 0:
                    fake[f"{name}.{col}"] = int(n)
    add("Valeurs manquantes", "Vides déguisés (« », « \\N », « NA »…)", "ok" if not fake else "ko",
        "Aucun : les valeurs manquantes sont de vrais NULL." if not fake else
        " · ".join(f"{k} : {v}" for k, v in fake.items()))

    # Cohérence
    n = int((f.origin == f.dest).sum())
    add("Cohérence", "Vols dont l'origine = la destination", "ok" if n == 0 else "ko", f"{n} vol(s).")
    return out


def checks_table(checks: list[dict]):
    rows = []
    for c in checks:
        color, label = BADGES[c["status"]]
        rows.append(ui.tags.tr(
            ui.tags.td(c["cat"], class_="text-muted text-nowrap"),
            ui.tags.td(c["ctrl"]),
            ui.tags.td(ui.span(label, class_=f"badge text-bg-{color}")),
            ui.tags.td(c["result"]),
        ))
    return ui.div(ui.tags.table(
        ui.tags.thead(ui.tags.tr(*[ui.tags.th(h) for h in ("Catégorie", "Contrôle", "Statut", "Résultat")])),
        ui.tags.tbody(*rows),
        class_="table table-sm align-middle mb-0",
    ), style="overflow-x:auto;")


def _constraints(meta, table, kind):
    return [c for c in meta["constraints"] if c["table"] == table and c["type"] == kind]


def _cols(definition: str) -> str:
    m = re.search(r"\(([^)]*)\)", definition)
    return m.group(1) if m else definition


def schema_table(meta) -> pd.DataFrame:
    rows = []
    for t in meta["tables"]:
        name = t["table"]
        pk = ", ".join(_cols(c["definition"]) for c in _constraints(meta, name, "PK"))
        uq = " ; ".join(_cols(c["definition"]) for c in _constraints(meta, name, "UNIQUE"))
        fks = " ; ".join(
            re.sub(r"FOREIGN KEY \(([^)]*)\) REFERENCES (?:\w+\.)?(\w+)\(([^)]*)\).*", r"\1 → \2.\3", c["definition"])
            + ("" if c["validated"] else " (NOT VALID)")
            for c in _constraints(meta, name, "FK"))
        rows.append({"Table": name, "Lignes": fmt_int(t["rows"]), "Clé primaire": pk or "–",
                     "UNIQUE": uq or "–", "Clés étrangères": fks or "–"})
    return pd.DataFrame(rows)


def declared_fk(meta, child, cols, parent):
    """Contrainte FK déclarée en base pour cette relation (ou None)."""
    if not meta:
        return None
    want = [c.strip() for c in cols.split(",")]
    for c in _constraints(meta, child, "FK"):
        m = re.match(r"FOREIGN KEY \(([^)]*)\) REFERENCES (?:\w+\.)?(\w+)\(", c["definition"])
        if m and [x.strip() for x in m.group(1).split(",")] == want and m.group(2) == parent:
            return c
    return None


def relations_table(app, checks) -> pd.DataFrame:
    meta = app.get("db_meta")
    by_label = {c["ctrl"]: c for c in checks}
    rows = []
    for label, child, cols, parent, card in RELATIONS:
        fk = declared_fk(meta, child, cols, parent)
        declared = "non lu (mode local)" if not meta else (
            "non" if fk is None else ("oui (NOT VALID)" if not fk["validated"] else "oui"))
        check_label = {"flights.carrier → airlines.carrier": "flights.carrier → airlines",
                       "flights.origin → airports.faa": "flights.origin → airports",
                       "flights.dest → airports.faa": "flights.dest → airports",
                       "flights.tailnum → planes.tailnum": "flights.tailnum → planes",
                       "weather.origin → airports.faa": "weather.origin → airports"}.get(label, "flights → weather")
        status = by_label[check_label]["status"]
        rows.append({"Relation": label, "Cardinalité": card, "Déclarée en base (FK)": declared,
                     "Respectée par les données": {"ok": "oui", "warn": "partiellement", "ko": "non"}[status]})
    rows.append({"Relation": "compagnies ↔ aéroports", "Cardinalité": "N–N, via la table flights",
                 "Déclarée en base (FK)": "via les FK de flights", "Respectée par les données": "–"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- interface

def _li(ok: bool, text: str):
    return ui.tags.li(ui.span("✓ " if ok else "✗ ", class_="text-success fw-bold" if ok else "text-danger fw-bold"),
                      text)


def security_section(app):
    meta = app.get("db_meta")
    items = [
        _li(True, "Connexion chiffrée : sslmode=require, côté app comme côté import Colab."),
        _li(True, "Mots de passe hors du code : secret DATABASE_URL dans Colab, fichier .env (ignoré par git) "
                  "côté app."),
        _li(True, "Connexion par le Session pooler de Supabase (compatible IPv4)."),
    ]
    if meta:
        tables = meta["tables"]
        read_only = all(t["privileges"]["SELECT"] and not any(t["privileges"][p] for p in ("INSERT", "UPDATE", "DELETE"))
                        for t in tables)
        rls = [t["table"] for t in tables if t["rls"] and t["policies"]]
        items += [
            _li(read_only, f"L'app se connecte avec le rôle « {html.escape(meta['user'])} » : "
                           + ("lecture seule (SELECT) sur les 5 tables, aucun droit d'écriture ni de suppression."
                              if read_only else "ce rôle a des droits d'écriture, il devrait être en lecture seule.")),
            _li(len(rls) == len(tables), f"Row Level Security activée avec une policy de lecture sur "
                                         f"{len(rls)}/{len(tables)} tables : {', '.join(rls) or 'aucune'}."),
        ]
    else:
        items.append(ui.tags.li("Droits et RLS lus en direct uniquement avec DATA_SOURCE=supabase."))
    return ui.tags.ul(*items, class_="list-unstyled mb-0")


@module.ui
def mission2_ui(app):
    meta = app.get("db_meta")
    checks = quality_checks(app)
    n_ko = sum(c["status"] == "ko" for c in checks)
    n_warn = sum(c["status"] == "warn" for c in checks)

    return ui.TagList(
        ui.p("Base de données de l'équipe, hébergée sur Supabase (PostgreSQL). "
             + (f"Structure lue dans la base le {meta['read_at']}." if meta else "Mode local : structure non lue."),
             class_="text-muted small"),
        ui.navset_card_underline(
            ui.nav_panel(
                "Pipeline d'import",
                ui.p("Les 5 fichiers fournis ont chacun un format différent. Le notebook Colab les lit avec pandas, "
                     "les nettoie, puis les importe dans Supabase.",
                     ui.a(" Ouvrir le notebook Colab ↗", href=COLAB_URL, target="_blank", rel="noopener")),
                html_table(SOURCES),
                ui.h6("Import dans PostgreSQL", class_="mt-4"),
                ui.tags.ol(
                    ui.tags.li("Connexion avec le secret DATABASE_URL (Session pooler, sslmode=require)."),
                    ui.tags.li("Une seule transaction : TRUNCATE des 5 tables (RESTART IDENTITY), puis COPY par lots "
                               "de 10 000 lignes. En cas d'erreur, rien n'est modifié."),
                    ui.tags.li("Vérification des nombres de lignes dans le SQL Editor de Supabase."),
                ),
                ui.h6("Lignes en base", class_="mt-3"),
                html_table(pd.DataFrame([{"Table": t["table"], "Lignes": fmt_int(t["rows"])} for t in meta["tables"]]))
                if meta else ui.p("Disponible avec DATA_SOURCE=supabase.", class_="text-muted"),
            ),
            ui.nav_panel(
                "Schéma & relations",
                ui.h6("Tables et contraintes déclarées"),
                html_table(schema_table(meta)) if meta else ui.p("Disponible avec DATA_SOURCE=supabase.",
                                                                class_="text-muted"),
                ui.h6("Relations attendues par l'énoncé", class_="mt-4"),
                html_table(relations_table(app, checks)),
                ui.p("« NOT VALID » : la contrainte s'applique aux nouvelles lignes, sans vérifier les lignes "
                     "existantes. La relation vers weather n'est pas déclarée : la météo ne couvre qu'une partie "
                     "des vols.", class_="text-muted small mt-2"),
            ),
            ui.nav_panel(
                f"Contrôles qualité ({n_ko} problème{'s' if n_ko > 1 else ''}, {n_warn} à noter)",
                ui.p("Contrôles demandés par l'énoncé, recalculés sur les données : clés étrangères, clés primaires, "
                     "nomenclature des codes par expressions régulières.", class_="text-muted"),
                checks_table(checks),
            ),
            ui.nav_panel("Sécurité", security_section(app)),
        ),
    )


@module.server
def mission2_server(input, output, session):
    pass  # tout le contenu est calculé une fois, au démarrage
