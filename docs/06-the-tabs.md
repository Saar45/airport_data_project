# 6. The tabs, one by one

The brief asks for "le maximum d'éléments (reporting à partir des données du passé) pour prédire les problèmes et ainsi mieux se préparer". Each tab answers one question the manager could act on.

The **left sidebar filters** (origin airport, carriers, destinations, months) apply to every tab except Prédiction. An empty selection means "all". The destination list includes the 4 airports that were missing from the `airports` table (SJU, BQN, STT, PSE).

Figures quoted below are for the full local dataset with no filter.

---

## Vue d'ensemble: "How bad is it overall?"
File: `modules/overview.py`

- **4 value boxes**: number of flights (336,776), cancellation rate (2.5 %), share of flights more than 15 min late (23.6 %), average arrival delay (6.9 min).
- **Monthly chart**: bars = number of flights, red line = problem rate.

**Talking point:** traffic is fairly flat across the year, but problems are not. **December and June–July** are the worst months, and September–November are the calmest. That points to winter storms and summer storms/holiday peaks.

---

## Mission 1: the 8 exploration questions
File: `modules/mission1.py`

One sub-tab per question (Q1 to Q8), with the brief's question in italics. Same logic as the team's notebook `Mission1_Exploration.ipynb`, but **recomputed from the Supabase data** each time the cache is rebuilt, so the answers always match the database. This tab ignores the sidebar filters.

Where the database was corrected after the notebook ran, the app shows both values. For example, Q1 says 27 airports without daylight saving time: 23 in the supplied file (the brief's expected answer) plus the 4 airports added in Mission 2. Two notebook figures changed for the same reason: Seattle has 856 unique planes, not 857, and the blank tail number no longer tops the "most take-offs" list. In both cases the notebook was counting the blank `tailnum` as a plane.

---

## Mission 2: the database
File: `modules/mission2.py`

- **Pipeline d'import**: the 5 source files (JSON, Excel, HTML, PDF), how each is read and cleaned, the import method from the team's Colab notebook (link included), and the row counts in the database.
- **Schéma & relations**: primary keys, UNIQUE constraints and foreign keys **read live from Supabase**, and for each relation the brief expects: whether it is declared in the database, and whether the data respects it.
- **Contrôles qualité**: the checks the brief asks for, recomputed on the data, with OK / À noter / Problème badges. They cover foreign keys, key uniqueness, code formats checked with regex, and missing values disguised as text.
- **Sécurité**: encrypted connection, the app's read-only role (privileges checked in the database), and Row Level Security.

The schema and security parts are read when the cache is built. After a change in Supabase, rebuild the cache to see it.

---

## Quand ?: "At what moments should we expect trouble?"
File: `modules/temporal.py`

- **Heatmap** of day of the week × scheduled departure hour, coloured by problem rate. Cells with fewer than 20 flights are hidden, because a rate on 3 flights means nothing.
- **Daily line**: the problem rate for every day of 2013.
- **10 most critical days** table.

**Talking point:** this is the strongest chart for preparation. **The risk climbs steadily through the day: 11 % of flights at 5h have a problem, 17 % at 8h, 25 % at 13h, 35 % at 18h and 39 % at 21h.** Delays build up as each late plane delays its next flight. By day, **Thursday (30 %) and Friday (29 %) are the worst, and Saturday the calmest (19 %)**. The critical days are mostly in winter: 8 February 2013 was the "Nemo" blizzard, and two thirds of flights had a problem that day or worse. Those days are when you staff up and plan for overnight passengers.

---

## Compagnies & routes: "Who and where?"
File: `modules/carriers.py`

- **Bar chart**: problem rate per airline (airlines with ≥ 100 flights). Hover to see the cancellation rate and number of flights.
- **Routes table**: origin → destination pairs with ≥ 100 flights, sorted by problem rate. The table has filters, so type in the column header to search.

**Talking point:** which airlines and routes need closer follow-up or negotiation. Hawaiian and Alaska Airlines have the fewest problems, Frontier and Mesa the most. Filter on one airport in the sidebar to see whether the ranking changes.

---

## Météo: "How much does weather matter?"
File: `modules/weather.py`

Choose a variable (visibility, wind, precipitation, temperature) to see the problem rate by range of that variable.

**Talking point:** bad weather roughly **doubles** the risk.
- Visibility: 23 % of flights have a problem in clear skies (10 miles), against **52 %** below 1 mile.
- Rain: 24 % when dry, **50 %** with even light rain, **65 %** with heavy rain.
- Wind: rises steadily, from 21 % (calm) to **40 %** above 25 mph.

Weather is forecastable a few days ahead, so this is where the "anticipate" story is most concrete.

**Limit to mention:** weather is only known at the **departure** airport (EWR, JFK, LGA), not at the destination.

---

## Avions: "Does the aircraft matter?"
File: `modules/planes.py`

- **Value box**: share of flights whose plane is known (≈ 84 %), with the explanation of why the rest is missing.
- Problem rate by **plane age** and by **manufacturer** (8 most common).

**Talking point:** plane age shows **no clear trend**: between 21 % and 27 % for every age group, and the oldest planes are not worse. Compared with time of day (11 % → 39 %) or weather (23 % → 52 %+), the effect is weak. That is a finding in itself: the problem is operational, not the fleet.

---

## Carte: "Where do the flights go?"
File: `modules/map.py`

Every destination: **size = number of flights**, **colour = problem rate**. Hover for details. The colour scale stops at the 95th percentile, so a couple of tiny routes at 100 % don't wash out all the other colours.

**Talking point:** a visual opener for the presentation.

---

## Prédiction: "What's the risk for this flight?"
File: `modules/predict.py`

Pick a scenario in the inner sidebar (airline, origin, month, departure hour, visibility, wind, rain):
- **Probabilité de problème**: the model's estimate for that scenario.
- **Moyenne historique**: the average rate (≈ 26 %), for comparison.
- **Curve**: the same scenario at every departure hour from 5h to 23h. The dotted line marks the hour you chose.

**Demo idea:** start with a 7h, clear-sky flight (low risk), then move to 19h with low visibility and wind. The probability jumps, and the curve shows by how much.

How the model works and its limits: [07-prediction-model.md](07-prediction-model.md).
