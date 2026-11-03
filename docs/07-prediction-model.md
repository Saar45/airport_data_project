# 7. The prediction model (`app/model.py`)

## What it predicts

For a given flight scenario, the model returns the **probability that the flight has a problem**: more than 15 min late on arrival, cancelled or diverted. It's a yes/no question, so we use a **classification** model.

## The model: logistic regression

Logistic regression is the classic first model for a yes/no outcome. It is `glm(..., family = binomial)` in R. It learns one weight per input. A positive weight pushes the probability up, a negative one pushes it down. The weighted sum is squeezed into a probability between 0 and 1.

We chose it because it's **fast, stable and easy to explain** in a presentation. It is a baseline, not the best possible model.

## Inputs (features)

| Feature | Type | How it's used |
|---|---|---|
| `carrier` | category | one yes/no column per airline (**one-hot encoding**) |
| `origin` | category | one-hot (EWR / JFK / LGA) |
| `month` | category | one-hot. Treated as a category, not a number, because December isn't "12× January" |
| `hour` | number | scheduled departure hour |
| `visib`, `wind_speed`, `precip` | numbers | weather at the origin airport at that hour |

Numbers are **standardized** (rescaled to mean 0, standard deviation 1), so weights are comparable and the training converges.

**Missing weather.** In the Supabase data, only 18 % of flights have weather (EWR, January to May). If flights without weather were dropped, the model would only know EWR and those 5 months. Instead, each missing weather value is replaced by the typical (median) value, and an extra yes/no column "weather unknown" is added (`SimpleImputer(add_indicator=True)`). The model therefore learns the weather effect only from flights that really have weather, while airline, airport, month and hour are learned from all flights.

## How it's trained

```python
pipe = Pipeline([
    ("prep", ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT),   # categories → 0/1 columns
        ("num", StandardScaler(), NUM),                         # numbers → standardized
    ])),
    ("clf", LogisticRegression(max_iter=1000)),                 # the model itself
])
```

A scikit-learn **Pipeline** chains the preparation steps and the model. When you call `predict`, the same preparation is automatically applied to the new scenario. Nothing can be forgotten.

Steps in `fit_problem_model()`:
1. Keep all flights (with or without weather), except the impossible wind speed (~1,048 mph).
2. Take a **random sample of 50,000 flights**, with a fixed seed (2013) so results are reproducible. That's plenty for this model and keeps startup fast.
3. Split **80 % training / 20 % test**, keeping the same share of problems in both (`stratify`).
4. Train on the 80 %, measure on the 20 % the model has never seen.

## How good is it? AUC ≈ 0.68 on the Supabase data

The **AUC** (area under the ROC curve) answers this question: *take one flight that had a problem and one that didn't. How often does the model give the higher risk to the right one?*
- 0.5 = coin toss, 1.0 = perfect.
- **0.68** means the model ranks the risky flight higher about 2 times out of 3. The exact value is shown under the Prédiction tab and changes when the cache is rebuilt.
- Weather is the strongest signal, so the score would improve if more flights had weather data.

That's reasonable for so few features. Delays depend on many things the data doesn't contain: crew, air-traffic control, the previous flight of the same plane, and so on.

## Limits to state honestly

- **Correlation, not causation.** "Evening flights have more problems" doesn't prove the hour *causes* it. It's the accumulation of delays during the day.
- **Weather is only at the departure airport**, and it is the *observed* weather, not a forecast. In real use you'd plug in forecasts.
- **The weather effect is learned only from EWR, January to May.** Applying it to JFK, LGA or summer months assumes weather has the same effect there.
- **One year of data (2013)**, three airports.
- **Linear effects only.** The model assumes the risk rises steadily with the hour, which is why the Prédiction curve is so smooth. Reality is bumpier (see the Quand ? heatmap).
- The model is retrained only when the cache is rebuilt.

## Ideas to improve it (if you have time)

1. Add the **day of the week** (`wday`) as a category.
2. Treat **hour as a category** instead of a number, to capture the real shape seen in the heatmap.
3. Try a **tree-based model** (`RandomForestClassifier` or `HistGradientBoostingClassifier` in scikit-learn). They capture interactions like "rain *and* evening" automatically, and usually score higher.
4. Show the **most influential features** in the tab (the model's weights), to explain *why* the risk is high.
5. Predict **delay in minutes** (regression) in addition to the yes/no.

Any change here requires rebuilding the cache (`REFRESH_CACHE=true` or delete `app/cache/`).
