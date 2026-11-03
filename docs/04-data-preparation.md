# 4. Data preparation (`app/data_prep.py`)

This is where the raw tables become the single `flights` table used by the app. Every decision below can be defended in the presentation.

## The 5 raw tables

| Table | One row = | Key |
|---|---|---|
| `flights` | one flight leaving NYC in 2013 (336,776 rows locally) | no natural single key |
| `airports` | one airport | `faa` code |
| `airlines` | one airline | `carrier` code |
| `planes` | one plane | `tailnum` |
| `weather` | one hour of weather at one NYC airport | `origin + year + month + day + hour` |

## Step by step

### 1. Column names to lowercase
```python
raw = {k: v.rename(columns=str.lower) for k, v in raw.items()}
```
Databases sometimes return `Year` or `YEAR`. Lowercase everywhere means the rest of the code never has to worry about it.

### 2. Add the 4 missing airports
The brief warns that 4 destinations appear in `flights` but not in `airports`: **BQN, PSE, SJU, STT** (Puerto Rico and the US Virgin Islands). Without them those flights would have no name and no map position. `MISSING_AIRPORTS` adds them with their names and coordinates, but only if they are still missing, so if your teammates add them to the database, nothing is duplicated.

### 3. Remove duplicate weather rows
`weather` should have one row per airport per hour, but a few hours appear twice. This happens at the daylight-saving time change in November. When joined to flights, those duplicates would **duplicate flights** and distort every count. `drop_duplicates(...)` keeps one row per key.

### 4. Clean manufacturer names in `planes`
The same company appears under several spellings (`AIRBUS` / `AIRBUS INDUSTRIE`, several `MCDONNELL DOUGLAS` variants). They are merged so the Avions tab doesn't split one manufacturer into three bars.

### 5. New columns on each flight

| Column | Rule | Why |
|---|---|---|
| `date` | built from year, month, day | daily charts |
| `wday` | day of the week (Lun … Dim) | heatmap |
| `cancelled` | `dep_time` is missing | a cancelled flight never departs, and the data has no "cancelled" column |
| `flown` | not cancelled | denominator for the delay rate |
| `diverted` | departed but `arr_delay` is missing | it left but never arrived where planned |
| `delayed` | flown, not diverted, `arr_delay > 15` | 15 min is the official US threshold for "late" |
| `problem` | cancelled **or** diverted **or** delayed | the main indicator of the app |

Locally that gives **8,255 cancelled** flights, **1,175 diverted** flights, and a **problem rate of 25.9 %**.

### 6. Joins (all *left* joins)

```python
f.merge(airlines, on="carrier", how="left", validate="many_to_one")
 .merge(airports, on="dest",    ...)     # → dest_name
 .merge(weather,  on=["origin","year","month","day","hour"], ...)  # → temp, wind_speed, precip, visib
 .merge(planes,   on="tailnum", ...)     # → plane_year, manufacturer, model, seats
```

- **Left join** keeps every flight even when the other table has no match. That matters because the brief says the foreign keys are not reliable. A normal (inner) join would silently drop flights.
- **`validate="many_to_one"`** is a safety check. If the right-hand table ever has duplicate keys (like the weather duplicates above), pandas raises an error instead of silently multiplying rows.
- The weather join uses the **hour of scheduled departure** at the **origin** airport. Weather is only known for EWR, JFK and LGA, not at the destination.

### 7. Fill-ins after the joins

| Column | Rule |
|---|---|
| `carrier_name`, `dest_name` | fall back to the code when there's no match, so charts never show empty labels |
| `plane_known` | whether the plane was found in `planes` |
| `plane_age` | flight year − plane manufacturing year |

**Only 84 % of flights have a known plane.** The brief explains why: American Airlines (AA) and Envoy (MQ) report fleet numbers instead of tail numbers. The Avions tab shows this number openly, so nobody over-interprets the plane charts.

## Data-quality points worth mentioning in the presentation

- 4 airports were missing from the reference table, and the app adds them.
- Weather has duplicate hours at the daylight-saving change, and the app removes them.
- 16 % of flights cannot be linked to a plane.
- Manufacturer names are inconsistent.
- A wind speed of ~1,048 mph exists in the data (an obvious sensor error). The model ignores it (see [07-prediction-model.md](07-prediction-model.md)).
- The local dataset has **336,776** flights, but the brief says **326,776**. Compare with the Supabase count once it's loaded.
