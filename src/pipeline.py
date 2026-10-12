"""CardPulse pipeline: cleaning, cohort retention, purchase funnel, RFM, product momentum, weekly forecast.

Input : data/raw/online_retail.csv (UCI Online Retail, fetched and SHA-256 checked by data/download.sh)
Output: outputs/*.csv and outputs/summary.json
"""
import json
import os
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")
os.makedirs(OUT, exist_ok=True)
S = {}

# ---------- 1. Clean ----------
df = pd.read_csv(os.path.join(ROOT, "data", "raw", "online_retail.csv"), dtype={"InvoiceNo": str, "StockCode": str})
S["raw_rows"] = len(df)
df = df[~df["InvoiceNo"].str.startswith("C")]
df = df[df["CustomerID"].notna()]
df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
S["clean_rows"] = len(df)
df["CustomerID"] = df["CustomerID"].astype(int)
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], format="%m/%d/%Y %H:%M")
df["Revenue"] = df["Quantity"] * df["UnitPrice"]
S["customers"] = int(df["CustomerID"].nunique())
S["products"] = int(df["StockCode"].nunique())
S["revenue_gbp"] = round(float(df["Revenue"].sum()), 2)
S["date_range"] = [str(df["InvoiceDate"].min().date()), str(df["InvoiceDate"].max().date())]

# ---------- 2. Cohort retention ----------
df["Month"] = df["InvoiceDate"].dt.to_period("M")
first = df.groupby("CustomerID")["Month"].min().rename("Cohort")
d = df.join(first, on="CustomerID")
d["Age"] = (d["Month"] - d["Cohort"]).apply(lambda x: x.n)
counts = d.groupby(["Cohort", "Age"])["CustomerID"].nunique().unstack()
ret = counts.div(counts[0], axis=0).round(3)
ret.index = ret.index.astype(str)
ret.to_csv(os.path.join(OUT, "cohort_retention.csv"))
# Dec 2011 holds only 9 days, so any cohort-month that lands in it is understated; exclude those cells
last_full = pd.Period("2011-11", "M")
cells = d[d["Month"] <= last_full]
c2 = cells.groupby(["Cohort", "Age"])["CustomerID"].nunique().unstack()
r2 = c2.div(c2[0], axis=0)
w = c2[0]
for k in (1, 3):
    valid = r2[k].notna()
    S[f"m{k}_retention_customer_weighted"] = round(float((r2.loc[valid, k] * w[valid]).sum() / w[valid].sum()), 4)
    S[f"m{k}_retention_unweighted_mean"] = round(float(r2.loc[valid, k].mean()), 4)

# ---------- 3. Funnel ----------
orders = df.groupby("CustomerID")["InvoiceNo"].nunique()
funnel = pd.DataFrame({
    "Stage": ["All buyers", "Repeat buyers (2+ orders)", "Loyal buyers (5+ orders)"],
    "Count": [len(orders), int((orders >= 2).sum()), int((orders >= 5).sum())],
})
funnel["Rate"] = (funnel["Count"] / len(orders)).round(3)
funnel.to_csv(os.path.join(OUT, "purchase_funnel.csv"), index=False)
S["funnel"] = funnel.set_index("Stage")["Count"].to_dict()

# ---------- 4. RFM (quartile scores, standard named segments) ----------
snapshot = df["InvoiceDate"].max() + pd.Timedelta(days=1)
rfm = df.groupby("CustomerID").agg(recency=("InvoiceDate", lambda x: (snapshot - x.max()).days),
                                   frequency=("InvoiceNo", "nunique"), monetary=("Revenue", "sum"))
rfm["R"] = pd.qcut(rfm["recency"], 4, labels=[4, 3, 2, 1]).astype(int)
rfm["F"] = pd.qcut(rfm["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
rfm["M"] = pd.qcut(rfm["monetary"], 4, labels=[1, 2, 3, 4]).astype(int)


def segment(r):
    if r.R >= 3 and r.F >= 3 and r.M >= 3:
        return "Champions"
    if r.R >= 3 and r.F >= 2:
        return "Loyal / growing"
    if r.R >= 3:
        return "New / one-off"
    if r.F >= 3 or r.M >= 3:
        return "At risk (valuable, lapsing)"
    return "Lapsed"


rfm["Segment"] = rfm.apply(segment, axis=1)
rfm.round(2).to_csv(os.path.join(OUT, "rfm_segments.csv"))
seg = rfm.groupby("Segment").agg(customers=("monetary", "size"), revenue=("monetary", "sum"))
seg["revenue_share"] = (seg["revenue"] / seg["revenue"].sum()).round(3)
seg.round(2).to_csv(os.path.join(OUT, "rfm_segment_summary.csv"))
S["rfm_segments"] = {k: {"customers": int(v.customers), "revenue_share": float(v.revenue_share)} for k, v in seg.iterrows()}
top20 = rfm["monetary"].sort_values(ascending=False)
S["top_20pct_customers_revenue_share"] = round(float(top20.head(int(len(top20) * 0.2)).sum() / top20.sum()), 3)

# ---------- 5. Product momentum ----------
end = pd.Timestamp("2011-12-01")  # last full month boundary
recent = df[(df["InvoiceDate"] >= end - pd.Timedelta(days=90)) & (df["InvoiceDate"] < end)]
prior = df[(df["InvoiceDate"] >= end - pd.Timedelta(days=180)) & (df["InvoiceDate"] < end - pd.Timedelta(days=90))]
mom = pd.DataFrame({"recent_rev": recent.groupby("Description")["Revenue"].sum(),
                    "prior_rev": prior.groupby("Description")["Revenue"].sum()}).fillna(0)
mom = mom[mom["prior_rev"] > 50]
mom["momentum"] = ((mom["recent_rev"] - mom["prior_rev"]) / mom["prior_rev"]).round(3)
mom["christmas_item"] = mom.index.str.contains("CHRISTMAS|XMAS|ADVENT|SANTA|REINDEER|SNOW", case=False)
top = mom.sort_values("momentum", ascending=False).head(20)
top.round(2).to_csv(os.path.join(OUT, "trending_products.csv"))
S["trending_top20_christmas_items"] = int(top["christmas_item"].sum())
top_ex = mom[~mom["christmas_item"]].sort_values("momentum", ascending=False).head(20)
top_ex.round(2).to_csv(os.path.join(OUT, "trending_products_ex_christmas.csv"))

# ---------- 6. Weekly revenue forecast ----------
wk = df.set_index("InvoiceDate")["Revenue"].resample("W-MON", label="left", closed="left").sum()
wk = wk[wk.index + pd.Timedelta(days=7) <= df["InvoiceDate"].max().normalize()]  # drop the partial final week
wk = wk[wk.index >= "2010-12-06"]  # drop the partial first week (data starts Wed 1 Dec 2010)
wk.rename("revenue").to_frame().to_csv(os.path.join(OUT, "weekly_revenue.csv"))
S["weekly_points"] = int(len(wk))


def mape(a, f):
    return float(np.mean(np.abs((a - f) / a)))


# Rolling-origin evaluation: forecast 4 weeks ahead from each origin over the last 16 weeks
H, first_origin = 4, len(wk) - 16
rows = []
for o in range(first_origin, len(wk) - H + 1):
    train, test = wk.iloc[:o], wk.iloc[o:o + H].values
    hw = ExponentialSmoothing(train, trend="add", seasonal=None, damped_trend=True).fit()
    rows.append({"origin": str(wk.index[o].date()),
                 "holt_damped": mape(test, hw.forecast(H).values),
                 "naive_last": mape(test, np.repeat(train.iloc[-1], H)),
                 "mean_4wk": mape(test, np.repeat(train.iloc[-4:].mean(), H))})
cv = pd.DataFrame(rows)
cv.round(4).to_csv(os.path.join(OUT, "forecast_rolling_origin.csv"), index=False)
S["forecast_origins"] = int(len(cv))
S["forecast_mape_4wk_ahead"] = {k: round(float(cv[k].mean()), 4) for k in ("holt_damped", "naive_last", "mean_4wk")}
S["forecast_holt_beats_mean4wk_origins"] = int((cv["holt_damped"] < cv["mean_4wk"]).sum())

with open(os.path.join(OUT, "summary.json"), "w") as f:
    json.dump(S, f, indent=2, default=str)
print(json.dumps(S, indent=2, default=str))
