# 3. Architecture: how the pieces fit together

## The big picture

There are two phases: **startup**, which runs once, and **interaction**, which runs every time someone clicks.

```
 STARTUP (once, when the app starts)
 ─────────────────────────────────────────────────────────────────────────
  .env ─► data_source.load_app_data()
              │
              ├─ cache file exists? ──yes──► read app/cache/<source>.pkl ──┐
              │                                                          │
              no                                                         │
              ▼                                                          │
         read_supabase()  or  read_local()      (5 raw tables)           │
              ▼                                                          │
         data_prep.prepare_data()   (clean + join → 1 big flights table) │
              ▼                                                          │
         model.fit_problem_model()  (train the prediction model)         │
              ▼                                                          │
         save to app/cache/<source>.pkl ─────────────────────────────────┤
                                                                         ▼
                                                    APP = { "flights", "airports", "airlines",
                                                            "raw", "model", "db_meta",
                                                            "source", "cache_version" }

 INTERACTION (every time a user changes something)
 ─────────────────────────────────────────────────────────────────────────
  sidebar filters (origin, carriers, months)
              ▼
  flights()  ← filtered copy of APP["flights"]          (in app.py)
              ▼
  every tab module receives flights() ─► builds its charts and tables
  (except Prédiction, which uses APP["model"] and its own inputs)
```

## Why it's built this way

**1. Load once, share with everyone.** `APP` is created when `app.py` is first read, outside any user session. If 20 colleagues open the app during the presentation, the data still sits in memory only once and nobody waits for a download.

**2. One denormalized table.** Instead of joining tables inside each chart, `prepare_data()` joins everything up front: airline names, destination names, weather at departure, plane info. Each tab then works on one table, `flights`. That's simpler and faster.

**3. A cache on disk.** The 2013 data never changes, so there's no reason to re-download 336k rows from Supabase each time. The prepared data and the trained model are saved with `pickle`, Python's built-in way of saving any object to a file, like `saveRDS()` in R.

**4. Same code for local and Supabase.** Only the *reading* step differs (`read_local()` vs `read_supabase()`). Both return the same 5 tables, and everything after that is identical. That's why you can build the app offline and switch to Supabase by changing one line in `.env`.

**5. One file per tab (modules).** Each tab is self-contained in `app/modules/`. You can change the Météo tab without touching the others. See [05-shiny-basics.md](05-shiny-basics.md).

**6. Pure functions for charts.** Every module separates two things:
- **pure functions** such as `heatmap_figure(df)` or `routes_table(df)`: they take a DataFrame and return a chart or table. They know nothing about Shiny, so you can test them in a notebook;
- **Shiny wiring**: a few lines that call those functions with the filtered data.

**7. Raw tables and database metadata for the Mission tabs.** Besides the joined `flights` table, `APP["raw"]` keeps `airports`, `airlines`, `planes` and `weather` exactly as read from the database. Mission 1 answers and Mission 2 checks must reflect the database, not the app's corrections. `APP["db_meta"]` holds what `read_supabase_meta()` reads from Postgres: row counts, constraints, the app role's privileges and Row Level Security. It is `None` in local mode.

**8. Cache version.** `CACHE_VERSION` in `data_source.py` is saved in the cache. If you change what goes into `APP`, increase it: older caches are then rebuilt automatically instead of crashing the app.

## File by file

| File | Role | Key functions |
|---|---|---|
| `app/app.py` | Entry point. Loads data, defines the page (navbar, sidebar, tabs), the global filter, and connects every module. | `app_ui`, `server`, `flights()` |
| `app/data_source.py` | Where the data comes from, plus the cache. | `load_app_data`, `read_supabase`, `read_local`, `make_engine` |
| `app/data_prep.py` | Cleaning, derived columns, joins. | `prepare_data` |
| `app/model.py` | Prediction model. | `fit_problem_model`, `predict_problem` |
| `app/utils.py` | Shared constants (French month/day names, colours), French number formatting, the shared aggregation. | `summarise`, `kpis`, `fmt_pct`, `fmt_int`, `style` |
| `app/modules/*.py` | One tab each. | `<tab>_ui`, `<tab>_server`, `*_figure`, `*_table` |

## The shared aggregation: `summarise()`

Almost every chart calls `utils.summarise(df, by=...)`. It groups the flights and computes the same indicators everywhere:

| Column | Meaning |
|---|---|
| `n` | number of flights |
| `problem_rate` | share of flights with a problem (delayed, cancelled or diverted) |
| `cancel_rate` | share of flights cancelled |
| `delay_rate` | share of *flights that took off* that arrived > 15 min late |
| `avg_arr_delay` | average arrival delay in minutes (negative = early) |

```python
summarise(flights, "month")              # one row per month
summarise(flights, ["origin", "dest"])   # one row per route
summarise(flights)                       # one row for everything
```

Because all tabs use it, a "taux de problèmes" means exactly the same thing on every page.
