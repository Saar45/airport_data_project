"""Génère dumps/supabase_dump.sql : dump SQL complet des 5 tables de la base Supabase (Mission 2).

Usage (depuis la racine du projet, avec le .env rempli) :
    uv run python scripts/dump_supabase.py

Contenu du dump : tables, données, clés primaires / UNIQUE / étrangères, séquences, RLS et policies.
Il se recharge sur un serveur PostgreSQL 17+ vide avec :
    createdb airport && psql -d airport -f dumps/supabase_dump.sql

Choix techniques :
- `-t 'public.*'` plutôt que `--schema=public` : le dump ne contient pas `CREATE SCHEMA public`,
  qui échoue sur toute base neuve (le schéma public y existe déjà).
- `--no-owner --no-privileges` : pas de dépendance aux rôles internes de Supabase.
- `--enable-row-security` : obligatoire pour le rôle en lecture seule shiny_reader (RLS activée).
- Les policies RLS visent le rôle shiny_reader : un préambule le crée (sans droit de connexion)
  s'il n'existe pas, pour que le dump se recharge partout sans erreur.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dumps" / "supabase_dump.sql"
PG_DUMP_CANDIDATES = [shutil.which("pg_dump"), "/opt/homebrew/opt/libpq/bin/pg_dump", "/usr/local/opt/libpq/bin/pg_dump"]

PREAMBLE = """
-- Ajouté par scripts/dump_supabase.py : les policies RLS ci-dessous visent le rôle de l'app,
-- shiny_reader (lecture seule). On le crée, sans droit de connexion, s'il n'existe pas.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'shiny_reader') THEN
        CREATE ROLE shiny_reader NOLOGIN;
    END IF;
END
$$;

"""


def find_pg_dump() -> str:
    for path in PG_DUMP_CANDIDATES:
        if path and Path(path).exists():
            return path
    sys.exit("pg_dump introuvable. macOS : brew install libpq (version 17 ou plus).")


def main() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        sys.exit("Fichier .env introuvable : copier .env.example vers .env et le compléter.")
    e = dotenv_values(env_file)
    pg_dump = find_pg_dump()
    print(subprocess.run([pg_dump, "--version"], capture_output=True, text=True).stdout.strip())

    OUTPUT.parent.mkdir(exist_ok=True)
    # Identifiants transmis à pg_dump par les variables d'environnement standard de libpq,
    # lues depuis .env : rien n'est écrit en dur ni visible dans la ligne de commande.
    password = e.get("SUPABASE_PASSWORD") or ""
    pg_env = os.environ.copy()
    pg_env["PGSSLMODE"] = "require"
    pg_env["PGPASSWORD"] = password  # ggignore : valeur lue dans .env, pas un secret écrit en dur
    result = subprocess.run(
        [pg_dump, "-h", e["SUPABASE_HOST"], "-p", e.get("SUPABASE_PORT") or "5432",
         "-U", e["SUPABASE_USER"], "-d", e.get("SUPABASE_DB") or "postgres",
         "-t", f"{e.get('SUPABASE_SCHEMA') or 'public'}.*",
         "--no-owner", "--no-privileges", "--enable-row-security"],
        env=pg_env, capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.exit(f"pg_dump a échoué :\n{result.stderr}")

    sql = result.stdout
    if "CREATE SCHEMA" in sql:
        sys.exit("Le dump contient CREATE SCHEMA : il échouerait sur une base neuve.")
    # Préambule inséré juste avant les premières instructions SET de pg_dump.
    first_set = sql.index("\nSET ")
    OUTPUT.write_text(sql[:first_set] + "\n" + PREAMBLE + sql[first_set + 1:], encoding="utf-8")

    tables = re.findall(r"^COPY public\.(\w+) ", sql, flags=re.M)
    print(f"Dump écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1e6:.1f} Mo), tables : {', '.join(tables)}")


if __name__ == "__main__":
    main()
