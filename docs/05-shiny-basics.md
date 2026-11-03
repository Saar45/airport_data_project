# 5. How Shiny works

If you've seen Shiny for R, it's the same idea with different syntax.

## Two halves: UI and server

| | Role | In our code |
|---|---|---|
| **UI** | *What the page looks like*: layout, inputs (sliders, dropdowns), and empty placeholders for outputs. Built once. | `app_ui = ui.page_navbar(...)` in `app.py`, and every `*_ui()` function |
| **Server** | *What happens*: functions that compute outputs from inputs. Runs for each visitor. | `def server(input, output, session)` in `app.py`, and every `*_server()` function |

They are linked **by name (id)**:

```python
# UI: an input called "months" and an empty slot for a text called "n"
ui.input_slider("months", "Mois", 1, 12, (1, 12))
ui.output_text("n")

# SERVER: read the input with input.months(); fill the slot by naming a function "n"
@render.text
def n():
    return fmt_int(k()["n"])
```

- Inputs are read by **calling** them: `input.months()`, `input.origin()`. Note the parentheses.
- An output is filled by a function **with the same name** as its placeholder, decorated with a `@render...`.

## Reactivity: the magic part

You never write "when the slider moves, redraw the chart". Shiny works it out itself: when a function reads `input.months()`, Shiny remembers that link and **re-runs the function automatically** whenever the slider changes.

`@reactive.calc` creates a **shared intermediate result**. This is the most important one in the app:

```python
@reactive.calc
def flights():                      # in app.py
    df = APP["flights"]
    if input.origin():
        df = df[df.origin.isin(input.origin())]
    if input.carrier():
        df = df[df.carrier.isin(input.carrier())]
    lo, hi = input.months()
    return df[df.month.between(lo, hi)]
```

Every chart calls `flights()`. The filtering is done **once** per filter change, and all charts that use it update together. It's like a cached variable that refreshes itself. In R it's `reactive({...})`.

## The decorators you'll see

| Decorator | Meaning |
|---|---|
| `@reactive.calc` | a reusable intermediate result (see above) |
| `@render.text` | fills a `ui.output_text(...)` placeholder |
| `@render.data_frame` | fills a `ui.output_data_frame(...)` (an interactive table) |
| `@render_plotly` | fills an `output_widget(...)` with a Plotly chart (from `shinywidgets`) |
| `@module.ui` / `@module.server` | turns a function into a reusable **module** (see below) |

## Modules: one tab = one file

Without modules, every input and output id must be unique across the whole app: two tabs couldn't both have a chart called `"chart"`. A **module** gives each tab its own namespace, so ids only need to be unique *inside* the tab.

Each file in `app/modules/` has the same shape:

```python
@module.ui
def weather_ui():                         # the tab's layout
    return ui.card(
        ui.input_select("var", "Variable", {...}),
        output_widget("by_weather"),
    )

@module.server
def weather_server(input, output, session, flights):   # the tab's logic
    @render_plotly
    def by_weather():
        return weather_figure(flights(), input.var())
```

Then `app.py` plugs it in with an **id** ("weather"), used on both sides:

```python
ui.nav_panel("Météo", weather_ui("weather"))     # in the UI
weather_server("weather", flights)               # in the server, passing the filtered data
```

Note the `flights` argument. That's how the global filter reaches each tab: `app.py` passes the `flights` reactive calc to every module.

## Layout building blocks (from `shiny.ui`)

| Function | What it draws |
|---|---|
| `ui.page_navbar(...)` | the whole page: top bar with tabs + left sidebar |
| `ui.nav_panel("Title", ...)` | one tab |
| `ui.sidebar(...)` | a collapsible side panel (the global filters, the Prédiction scenario) |
| `ui.card(ui.card_header("..."), ...)` | a white box with a title. `full_screen=True` adds the expand button |
| `ui.value_box(title, value, showcase=icon)` | the big number tiles on Vue d'ensemble |
| `ui.layout_columns(a, b, col_widths=(8, 4))` | side-by-side columns (out of 12) |
| `ui.layout_column_wrap(..., width="220px")` | as many columns as fit, each at least 220px wide |
