# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Student data project ("Projet Trafic Aérien", ADP consultant scenario). The brief is `EnoncéProjetTraficAérien-Mission1Exploration.pdf`; read it for the exact questions. `app/` holds the Mission 3 web app. The other deliverables are `Mission1_Exploration.ipynb`, `Mission2_Import_Supabase.ipynb`, `sql/` (Mission 1 and 2 queries, reconstructed and verified against the database) and `dumps/supabase_dump.sql`.

`docs/` holds beginner-oriented documentation of the app (the owner is new to Python). Keep it in sync when behaviour changes. `docs/06-the-tabs.md` quotes figures computed from the local data, so re-check them if the data or definitions change.

## Commands

The environment is managed with `uv`, pinned to Python 3.12 (`.python-version`). The system Python is 3.15, which is too new for parts of the data stack.

```bash
uv sync                                   # install deps
uv run shiny run app/app.py --reload      # run the app (http://127.0.0.1:8000)
REFRESH_CACHE=true uv run shiny run app/app.py   # rebuild the data cache + model
```

Checks (the same steps the CI runs in `.github/workflows/ci.yml`, all on local data with no secrets):

```bash
uv run ruff check app tests scripts  # lint (bug-finding rules only, see [tool.ruff] in pyproject.toml)
uv run pytest -q                     # tests in tests/, run on local nycflights13 data
uv run pytest -q -k mission2         # a single test group
uv export --no-dev --no-emit-project --no-hashes --no-header -o app/requirements.txt   # after any dependency change
```

Deployment: the CI's `deploy` job (it runs only on `main`, after `check` passes) copies the git-tracked contents of `app/` to the `deploy` branch, force-pushed each time. Posit Connect Cloud publishes that branch, with primary file `app.py` and `requirements.txt` at its root. The notebooks at the repo root made Connect Cloud require `jupyter`, which is why it no longer deploys from `main`. Never edit the `deploy` branch by hand. `app/requirements.txt` must stay in sync with `uv.lock` (the CI checks it). Secrets are Connect Cloud "Variables" (the same names as in `.env`). Vercel was ruled out: it cuts Shiny's WebSocket session at the function's max duration (5 min on Hobby).

SQL dump (Mission 2 deliverable): `dumps/supabase_dump.sql` is committed on purpose, because it is handed in to the teacher. Regenerate it with `uv run python scripts/dump_supabase.py` (it needs `.env` and pg_dump 17+). The script uses `-t 'public.*'`, not `--schema=public`, so the dump has no `CREATE SCHEMA` and restores into an empty database. It also prepends the creation of the `shiny_reader` role, which the RLS policies reference. Check it restores with `psql -v ON_ERROR_STOP=1` into a fresh Postgres 17.

Configuration lives in `.env` at the repo root (copy `.env.example`). `DATA_SOURCE=local` uses the bundled `nycflights13` CSVs, so it works offline. `DATA_SOURCE=supabase` reads the team's database. Each module exposes pure `*_figure` / `*_table(df)` functions, and `tests/test_app.py` calls them on full, filtered and empty frames. Add a test there for any new chart or table.

## App architecture (`app/`)

- Data is loaded **once per process** at import time in `app.py` (`APP = load_app_data()`), then shared by all sessions. `data_source.py` reads all 5 tables (Supabase via SQLAlchemy + psycopg with `sslmode=require`, or local CSVs). `data_prep.prepare_data` does every join and derived column. `model.fit_problem_model` trains the demo model. The full result is pickled to `app/cache/<source>.pkl`. After changing prep or model code, delete the cache or set `REFRESH_CACHE=true`, otherwise you'll see stale data.
- `flights` is the single denormalized frame that every tab uses. Derived columns: `cancelled` (no `dep_time`), `diverted` (departed but no `arr_delay`), `delayed` (`arr_delay > 15`), `problem` (any of the three), `flown`, plus the joined `carrier_name`, `dest_name`, weather (`temp`, `wind_speed`, `precip`, `visib`) and planes (`plane_year`, `plane_age`, `manufacturer`, `plane_known`) columns.
- The database was corrected in Mission 2. It has 4 added airports (`MISSING_AIRPORTS`) and 716 added planes that have only a `tailnum` (`added_planes_mask`, to satisfy the `flights.tailnum` FK). The Mission tabs detect both, so the answers still quote the supplied files (the brief's expected values) and the Mission 2 checks still report the original FK problems.
- `APP["raw"]` holds the uncorrected `airports`, `airlines`, `planes` and `weather` tables. `APP["db_meta"]` holds the Postgres constraints, privileges and RLS (Supabase only). The Mission 1 and Mission 2 tabs use these and ignore the sidebar filters. Increase `CACHE_VERSION` in `data_source.py` whenever the shape of `APP` changes.
- `utils.summarise(df, by)` is the shared aggregation (n, cancel/delay/problem rates, average delay). Use it rather than writing new groupbys, so every tab stays consistent.
- Global sidebar filters (origin, carriers, destinations, months) produce one `reactive.calc` `flights` in `app.py`, which is passed to each module's server. The Prédiction tab deliberately ignores the filters.
- Each tab lives in `app/modules/<name>.py` as a Shiny `@module.ui` / `@module.server` pair. Plotly charts go through `shinywidgets` (`output_widget` + `@render_plotly`).
- The local `nycflights13` package can't be imported: its `__init__` needs `pkg_resources`. `read_local()` therefore reads the package's CSV files directly.

The work is split across a team:
- **Mission 1, exploration** (teammates): 8 questions on airports, carriers, destinations, Houston/Seattle flights, exclusive destinations, and so on. Answered in SQL first, then checked in Python/R.
- **Mission 2, DB** (teammates): rebuild the relational DB (SQL or NoSQL) and host it (Supabase, AWS, Azure, alwaysdata, …) behind a secured connection (DSN / credentials kept out of the code).
- **Mission 3, WebApp** (this repo owner, bonus points): a **Shiny for Python** app that connects to the Mission 2 database, hosted on **Supabase**. It should show reporting on past data that helps a manager *anticipate* problems (delays, cancellations, overnight stays at the airport). The brief calls this predictive analysis for decision support. It is shown at the final presentation, so it has to impress.

## Data model (nycflights13-style, BTS source)

326,776 flights that left NYC airports (JFK, LGA, EWR). Five tables:

| Table | Key | Notes |
|---|---|---|
| `flights` | composite `(year, month, day, hour, carrier, flight)`; `flight` alone is **not** unique | `dep_time`/`arr_time`/`sched_*` are HHMM or HMM integers in local time; `dep_delay`/`arr_delay` in minutes (negative = early); `time_hour` joins to weather |
| `airports` | `faa` (natural key, check format with a regex) | `dst`: A = US DST, U = unknown, N = no DST; `tzone` is IANA |
| `airlines` | `carrier` (2-letter code) | |
| `planes` | `tailnum` | AA and MQ report fleet numbers, not tail numbers, so they don't match |
| `weather` | composite `(year, month, day, hour, origin)` | hourly data for the 3 NYC origins only |

Relations: planes → flights is 1-to-many on `tailnum`. Carriers ↔ airports is many-to-many through `flights`.

Known integrity problems. The app's joins must handle these, so use left joins and don't assume FKs hold:
- 4 `dest` codes are missing from `airports`: BQN (Rafael Hernandez), PSE (Mercedita), SJU (San Juan), STT (Cyril E. King).
- Hundreds of `tailnum` values in `flights` are missing from `planes`.
- The brief says the provided schema diagram is not reliable ("à améliorer") and that there may be other FK problems.
- Cancelled flights show up as missing `dep_time` / `arr_time`, not as a flag column.

## Mission 3 conventions

- Supabase credentials come only from `.env` (git-ignored). Use the Session pooler host; the direct host is IPv6-only on the free tier. Prefer a read-only role for the app.
- Supabase `NUMERIC` columns arrive as `Decimal`. `_decimals_to_float` converts them, so keep that conversion if you change the loader.
- The local dataset has 336,776 flights; the brief says 326,776. Check row counts against Supabase once the teammates have loaded it.
- Write all UI text in French, with French number formatting (`fmt_pct`, `fmt_int`, `fmt_min` in `utils.py`; plotly `separators=", "`).
