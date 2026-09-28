import pandas as pd
import numpy as np
import psycopg2
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
 
# --- 1. Load data from PostgreSQL ---
conn = psycopg2.connect(**DB_CONFIG)
df = pd.read_sql("""SELECT
    EXTRACT(YEAR FROM AGE(dd.date, dc.dob))        AS age_at_event,
    dc.gender,
    dc.state                                        AS runner_state,
    dc.blood_group,
    CASE fr.distance
        WHEN '5K'       THEN 5
        WHEN '10K'      THEN 10
        WHEN 'Half'     THEN 21.1
        WHEN 'Full'     THEN 42.2
        ELSE 10 END                                 AS distance_km,
    de.marathon_type,
    de.event_category,
    dd.weekend_flag,
    dd.month,
    dd.quarter,
    COALESCE(ds.contribution_amount, 0)             AS sponsor_contribution,
    EXTRACT(EPOCH FROM fr.finish_time)              AS finish_time_seconds   -- TARGET
FROM public.fact_race_result  fr
JOIN public.dim_client        dc  ON fr.client_key   = dc.client_key
JOIN public.dim_event         de  ON fr.event_key    = de.event_key
JOIN public.dim_date          dd  ON fr.date_key     = dd.date_key
JOIN public.dim_sponsor       ds  ON fr.sponsor_key  = ds.sponsor_key
WHERE fr.finish_time IS NOT NULL
  AND dc.dob        IS NOT NULL;
""", conn)
conn.close()
 
# --- 2. Encode categoricals ---
cat_cols = ["gender", "runner_state", "blood_group", "marathon_type", "event_category"]
for col in cat_cols:
    df[col] = LabelEncoder().fit_transform(df[col].astype(str))
df["weekend_flag"] = df["weekend_flag"].astype(int)
 
# --- 3. Split features / target ---
FEATURES = ["age_at_event","gender","runner_state","blood_group","distance_km",
            "marathon_type","event_category","weekend_flag","month","quarter",
            "sponsor_contribution"]
X = df[FEATURES]
y = df["finish_time_seconds"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
 
# --- 4. Train ---
model = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)
 
# --- 5. Evaluate ---
y_pred = model.predict(X_test)
print(f"RMSE : {np.sqrt(mean_squared_error(y_test, y_pred)):.2f} seconds")
print(f"MAE  : {mean_absolute_error(y_test, y_pred):.2f} seconds")
print(f"R²   : {r2_score(y_test, y_pred):.4f}")
 
# --- 6. Feature importance ---
fi = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
print(fi)