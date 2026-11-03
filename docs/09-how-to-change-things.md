# 9. How to change things (recipes)

Run the app with `--reload` while you edit: the browser refreshes on every save. If something breaks, the error appears **in the terminal** where the app runs, and often in red in the page.

---

## Change a text, title or label

Search for the text in `app/` (Cmd + Shift + F in VS Code) and edit it. Card titles are in `ui.card_header("...")`, tab names in `ui.nav_panel("...")` in `app.py`.

## Change colours

Shared colours are at the top of `app/utils.py`:

```python
PROBLEM_COLOR = "#d9534f"     # red: bars and lines about problems
NEUTRAL_COLOR = "#9fb3c8"     # grey-blue: volumes
COLORSCALE = [[0, "#ffffcc"], [0.5, "#fd8d3c"], [1, "#bd0026"]]   # heatmap + map: yellow → red
```

The value-box colours are their `theme=` argument (`"danger"`, `"warning"`, `"primary"`, ...).

---

## Add a chart to an existing tab

Example: add "problem rate by airline" to the Météo tab. Three steps, all in `app/modules/weather.py`.

**1. Write a pure function that returns a figure:**
```python
def my_new_figure(df):
    d = summarise(df, "carrier_name")                       # one row per airline
    fig = go.Figure(go.Bar(x=d.carrier_name, y=d.problem_rate))
    fig.update_layout(yaxis=dict(tickformat=".0%"))         # show as %
    return style(fig)                                       # shared look
```

**2. Add a placeholder in the module's UI function** (pick a unique id):
```python
ui.card(ui.card_header("Mon nouveau graphique"), output_widget("my_chart")),
```

**3. Fill it in the module's server function.** The function name = the id:
```python
@render_plotly
def my_chart():
    return my_new_figure(flights())
```

**Tip:** test step 1 in a notebook first. Load the data with:
```python
import sys; sys.path.insert(0, "app")
from data_source import load_app_data
APP = load_app_data(source="local")
fig = my_new_figure(APP["flights"]); fig.show()
```

## Add a table

Same as above, but:
- the function returns a pandas DataFrame;
- the placeholder is `ui.output_data_frame("my_table")`;
- the decorator is `@render.data_frame`.

---

## Add a global filter (e.g. aircraft manufacturer)

All in `app/app.py`. The existing **Destinations** filter is a working example to copy.

**1. Add an input to the sidebar** (in `app_ui = ...`, inside `ui.sidebar(...)`):
```python
ui.input_selectize("manufacturer", "Constructeurs",
                   sorted(APP["flights"].manufacturer.dropna().unique()),
                   multiple=True, options={"placeholder": "Tous"}),
```

**2. Use it in the `flights()` function in `server`:**
```python
if input.manufacturer():
    df = df[df.manufacturer.isin(input.manufacturer())]
```

Every tab follows automatically, because they all use `flights()`.

---

## Add a new tab

**1. Create `app/modules/mytab.py`** by copying the smallest module (`weather.py` or `map.py`) and renaming:
```python
from shiny import module, ui
from shinywidgets import output_widget, render_plotly
from utils import style, summarise

@module.ui
def mytab_ui():
    return ui.card(ui.card_header("Mon onglet"), output_widget("chart"))

@module.server
def mytab_server(input, output, session, flights):
    @render_plotly
    def chart():
        ...
```

**2. Register it in `app/app.py`** in three places:
```python
from modules.mytab import mytab_server, mytab_ui           # with the other imports
ui.nav_panel("Mon onglet", mytab_ui("mytab")),              # in app_ui, with the other tabs
mytab_server("mytab", flights)                              # at the end of server()
```

---

## Add a column to the data

Add it in `prepare_data()` in `app/data_prep.py`, e.g.:
```python
f["long_haul"] = f.distance > 2000
```
Then **rebuild the cache** (delete `app/cache/`), or the app keeps using the old data without the column.

## Change the model

Edit `app/model.py` (e.g. add `"wday"` to `CAT`) and rebuild the cache. If you add an input feature, also add a matching input in `modules/predict.py`: in the sidebar of `predict_ui`, and in the `scenario()` DataFrame in `predict_server`.

---

## Add a Python library

```bash
uv add seaborn          # installs it and records it in pyproject.toml + uv.lock
```
Don't use `pip install`. It would install outside the project's environment.

## Quick check that nothing is broken

Without opening a browser, this loads the data and builds every chart with no filter and with an empty filter:
```bash
uv run python -c "
import sys; sys.path.insert(0, 'app')
from data_source import load_app_data
from modules import overview, temporal, carriers, weather, planes, map as m
from utils import summarise
APP = load_app_data(source='local'); f = APP['flights']
for df in (f, f.iloc[0:0]):
    overview.monthly_figure(df); temporal.heatmap_figure(df); carriers.carriers_figure(df)
    [weather.weather_figure(df, v) for v in weather.WEATHER_VARS]
    planes.age_figure(df); m.map_figure(df, APP['airports'])
print('OK')
"
```
