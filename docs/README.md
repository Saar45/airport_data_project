# Mission 3 web app: documentation

This folder explains the web app built for Mission 3 of the *Projet Trafic Aérien*. It is written for someone who knows data analysis but not much Python.

## What the app is

It is an interactive dashboard, built with **Shiny for Python**, about flights that left New York (JFK, LGA, EWR) in 2013. It answers one question for the manager: **when, where and why do flights go wrong, and can we predict it?**

A flight counts as having a **problem** if it was:
- **delayed**: it arrived more than 15 minutes late,
- **cancelled**: it never took off, or
- **diverted**: it took off but never arrived at its destination.

That is about 26 % of flights.

## Reading order

| File | What you'll learn |
|---|---|
| [01-getting-started.md](01-getting-started.md) | Install, run and stop the app. Common errors. |
| [02-python-basics.md](02-python-basics.md) | The Python you need to read this code, and nothing more. |
| [03-architecture.md](03-architecture.md) | How the pieces fit together, from the database to the charts. |
| [04-data-preparation.md](04-data-preparation.md) | Every cleaning and joining decision, and why. |
| [05-shiny-basics.md](05-shiny-basics.md) | How Shiny works: UI, server, reactivity, modules. |
| [06-the-tabs.md](06-the-tabs.md) | What each tab shows and how to talk about it in the presentation. |
| [07-prediction-model.md](07-prediction-model.md) | The prediction model explained simply, and its limits. |
| [08-supabase.md](08-supabase.md) | The database connection, security, and the problems we already hit. |
| [09-how-to-change-things.md](09-how-to-change-things.md) | Recipes: add a chart, a filter or a tab. Change colours. |

## Where things are

```
Airport_project/
├── .env                 ← your settings and DB password (never share or commit)
├── .env.example         ← template for .env
├── pyproject.toml       ← list of Python libraries the app needs
├── uv.lock              ← exact versions of those libraries (managed by uv)
├── .python-version      ← Python version for this project (3.12)
├── docs/                ← you are here
└── app/
    ├── app.py           ← entry point: page layout + global filters
    ├── data_source.py   ← reads the data (Supabase or local) + cache
    ├── data_prep.py     ← cleaning and joins
    ├── model.py         ← prediction model
    ├── utils.py         ← shared helpers (formatting, aggregates, colours)
    ├── cache/           ← saved copy of the prepared data (auto-generated)
    └── modules/         ← one file per tab
        ├── overview.py  mission1.py  mission2.py  temporal.py  carriers.py
        └── weather.py   planes.py    map.py       predict.py
```
