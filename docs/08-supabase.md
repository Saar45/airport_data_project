# 8. Supabase connection and security

Supabase is a hosted **PostgreSQL** database. Your teammates (Mission 2) create and fill it. The app only **reads** from it.

## How the app connects (`app/data_source.py`)

```python
url = URL.create("postgresql+psycopg", username=..., password=..., host=..., port=..., database=...)
engine = create_engine(url, connect_args={"sslmode": "require"})
```

- **SQLAlchemy** (`create_engine`) is the general database toolkit; **psycopg** is the Postgres driver underneath. Together they're the equivalent of `DBI` + `RPostgres` in R.
- `sslmode=require` means the connection is **encrypted**. The app refuses to connect otherwise.
- `pd.read_sql_table(...)` downloads each of the 5 tables into a DataFrame.
- The app then caches everything locally (see [01-getting-started.md](01-getting-started.md)), so Supabase is only contacted when the cache is rebuilt.

## The `.env` file

```
DATA_SOURCE=supabase
SUPABASE_HOST=aws-0-eu-west-1.pooler.supabase.com
SUPABASE_PORT=5432
SUPABASE_DB=postgres
SUPABASE_USER=shiny_reader.olqkxvifgalmtooaetwt
SUPABASE_PASSWORD=********
SUPABASE_SCHEMA=public
REFRESH_CACHE=false
```

`.env` holds the password. It is listed in `.gitignore`, so it is never committed. **Never paste it in a chat or a screenshot.**

## Three things that tripped us up (and why)

### 1. Use the *pooler* host, not the direct host
Supabase offers two hosts:
- `db.<project-ref>.supabase.co` (direct): **IPv6 only** on the free plan. Most home and school networks can't reach it, and you get `failed to resolve host`.
- `aws-0-<region>.pooler.supabase.com` (Session pooler): works everywhere.

With the pooler, the **user name includes the project ref**: `<role>.<project-ref>`, e.g. `shiny_reader.olqkxvifgalmtooaetwt`.

You find the host in the Supabase dashboard: **Connect** button → **Session pooler**.

### 2. The user must match the password
Supabase never displays a database password after creation, and an invited member can't reset it. So the app uses a **dedicated read-only role**, `shiny_reader`, created by the project owner:

```sql
create role shiny_reader login password '...';
grant usage on schema public to shiny_reader;
grant select on all tables in schema public to shiny_reader;
alter default privileges in schema public grant select on tables to shiny_reader;
```

If you put the `shiny_reader` password with user `postgres...`, you get `password authentication failed`.

**Why a read-only role?** If the app or its `.env` ever leaked, nobody could modify or delete the data. This answers the brief's requirement *"N'oubliez pas de sécuriser la connexion à la BD"*. Mention it in the presentation.

### 3. Row Level Security (RLS) can hide all rows
Supabase turns on **RLS** for tables created in its dashboard. With RLS on, a role only sees rows that a **policy** allows. With no policy, `SELECT` returns **0 rows and no error**. The owner (`postgres`) is exempt, so your teammates see their data while the app sees nothing.

The fix, run once by the owner in the SQL Editor:

```sql
create policy "app read" on public.flights  for select to shiny_reader using (true);
create policy "app read" on public.airports for select to shiny_reader using (true);
create policy "app read" on public.planes   for select to shiny_reader using (true);
create policy "app read" on public.weather  for select to shiny_reader using (true);
alter table public.airlines enable row level security;
create policy "app read" on public.airlines for select to shiny_reader using (true);
```

The app protects itself here: if any table comes back empty, it stops with the message `Tables vides côté supabase : ...` instead of saving an empty cache.

## What the app expects from the database

- 5 tables in schema `public`: `flights`, `airports`, `airlines`, `planes`, `weather`.
- The original column names (any letter case). Extra columns, like an `id`, are ignored.
- Postgres `NUMERIC` columns are fine: the app converts them to normal numbers (`_decimals_to_float`).

## Switching between local and Supabase

1. Edit `DATA_SOURCE` in `.env` (`local` ↔ `supabase`).
2. First time with a given source, or after the database changes: set `REFRESH_CACHE=true`, start the app once, then set it back to `false`.
3. The badge at the top right of the app shows which source is in use.
