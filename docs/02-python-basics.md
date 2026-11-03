# 2. Just enough Python to read this code

This page only covers what appears in the app. Where it helps, Python is compared to R.

## Indentation is the syntax

Python has no `{ }` for blocks: **indentation** defines what belongs inside a function, `if` or loop. Four spaces per level.

```python
def kpis(df):                 # function definition ends with ":"
    s = summarise(df)         # indented = inside the function
    if s.empty:               # if ... :
        return {"n": 0}       # inside the if
    return s.iloc[0].to_dict()
```

## Imports

```python
import pandas as pd                       # R: library(pandas), but you must write pd.xxx
from shiny import module, render, ui      # take only these names from the shiny library
from utils import fmt_pct, summarise      # our own file app/utils.py
from modules.map import map_ui            # our own file app/modules/map.py
```

Each `.py` file is a **module**, and you import names from it. That is how the app is split into files.

## Basic data types

```python
n = 336776                       # int
rate = 0.259                     # float
name = "JFK"                     # str (text)
ok = True                        # bool (TRUE in R)
tabs = ["EWR", "JFK", "LGA"]     # list, like c(...) in R; indexing starts at 0: tabs[0] == "EWR"
choices = {"UA": "United Air Lines Inc. (UA)"}   # dict = key → value (like a named list)
choices["UA"]                    # → "United Air Lines Inc. (UA)"
```

## f-strings (text with variables inside)

```python
f"Source : {APP['source']}"      # → "Source : local"
f"{100 * x:.1f} %"               # format with 1 decimal → "25.9 %"
```

That's like `paste0()` / `sprintf()` in R.

## Functions with default arguments

```python
def destinations_table(df, order="top", k=10):
    ...
destinations_table(flights)                    # uses order="top", k=10
destinations_table(flights, "bottom", k=5)
```

## List comprehensions

This is a compact loop that builds a list. You'll see it in a few places:

```python
x = [MOIS[int(m) - 1] for m in d.month]       # month numbers → month names
# R equivalent: MOIS[d$month]
```

## Decorators: the `@something` line above a function

A decorator **wraps** the function below it and gives it a special role. Shiny uses them everywhere:

```python
@render.text          # "this function produces the text output called `n`"
def n():
    return fmt_int(k()["n"])
```

For now, you can read `@render.text`, `@render_plotly`, `@reactive.calc` and `@module.ui` as **labels that tell Shiny what the function is for**. Details are in [05-shiny-basics.md](05-shiny-basics.md).

## pandas: the DataFrame library (≈ dplyr)

A **DataFrame** is a table, like an R `data.frame` / tibble.

| What you want | R (dplyr) | pandas |
|---|---|---|
| a column | `df$origin` | `df.origin` or `df["origin"]` |
| filter rows | `filter(df, origin == "JFK")` | `df[df.origin == "JFK"]` |
| filter with a list | `filter(df, carrier %in% x)` | `df[df.carrier.isin(x)]` |
| new column | `mutate(df, late = arr_delay > 15)` | `df["late"] = df.arr_delay > 15` |
| group + summarise | `group_by(month) \|> summarise(n = n())` | `df.groupby("month").agg(n=("problem", "size"))` |
| join | `left_join(a, b, by = "dest")` | `a.merge(b, on="dest", how="left")` |
| sort | `arrange(desc(n))` | `df.sort_values("n", ascending=False)` |
| top 10 | `slice_max(n, n = 10)` | `df.nlargest(10, "n")` |
| missing values | `is.na(x)` | `x.isna()` |
| rename | `rename(new = old)` | `df.rename(columns={"old": "new"})` |

Logical operators on columns are `&` (and), `|` (or), `~` (not). Use them **instead of** `and`, `or`, `not`:

```python
f["delayed"] = f.flown & ~f.diverted & (f.arr_delay > 15)
```

## Other libraries used

| Library | Role | R equivalent |
|---|---|---|
| `shiny` | the web app framework | `shiny` |
| `shinywidgets` | lets Shiny display Plotly charts | (built into `plotly::renderPlotly`) |
| `plotly` | interactive charts | `plotly` |
| `pandas`, `numpy` | data tables, maths | `dplyr`, base R |
| `scikit-learn` | machine learning (the prediction model) | `glm`, `caret`, `tidymodels` |
| `sqlalchemy`, `psycopg` | talking to the Postgres database (Supabase) | `DBI`, `RPostgres` |
| `python-dotenv` | reads the `.env` file | `.Renviron` |
| `faicons` | icons in the value boxes | `bsicons` / `icon()` |
| `nycflights13` | the local copy of the data | `nycflights13` |
