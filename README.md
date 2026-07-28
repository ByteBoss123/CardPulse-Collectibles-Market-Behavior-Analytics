# CardPulse: Collectibles Market Behavior Analytics

End-to-end behavioral analytics pipeline built to demonstrate the core data
science skills required for a consumer/marketplace analytics role — specifically
the kind of product analytics work Fanatics Collectibles does at scale.

## Problem

Online collectibles marketplaces need to answer three questions to run efficiently:
1. **Who is buying and coming back?** — retention and cohort analysis
2. **What is trending?** — product momentum signals for inventory and pricing decisions
3. **How much will we sell?** — demand forecasting for supply planning

## Dataset

UCI Online Retail Dataset (real UK e-commerce transactions, 2010–2011):
- 541,909 raw transactions → 397,884 after cleaning (removed cancellations, nulls, negative quantities)
- 4,338 unique customers
- 3,877 unique products
- £8.9M total revenue
- Cleaned with pandas: cancelled orders removed (InvoiceNo prefix "C"), CustomerID nulls dropped, Quantity/UnitPrice <= 0 excluded

## What's built

### 1. Cohort Retention Analysis
Monthly cohort retention matrix tracking what % of customers from each acquisition
cohort returned in subsequent months. Key finding: average month-1 retention is 20.6%,
stabilizing around 23% by month 3 — consistent with e-commerce industry benchmarks.

### 2. Purchase Funnel
- All buyers: 4,338
- Repeat buyers (2+ orders): 2,845 (65.6%)
- Loyal buyers (5+ orders): 1,114 (25.7%)

### 3. RFM Segmentation
Customers scored on Recency, Frequency, and Monetary value and segmented into:
- Champions: 1,679 (38.7%)
- Potential: 1,368 (31.5%)
- At Risk: 1,291 (29.8%)

### 4. Trending Products
Revenue momentum score computed as (recent 90-day revenue - prior 90-day revenue) /
prior 90-day revenue, filtered to products with >£50 prior-period baseline to
exclude noise. Top trending products identified with momentum scores up to 40x.

### 5. Demand Forecast
Holt-Winters additive exponential smoothing on weekly revenue (53 weeks):
- Test MAPE: 21.3%
- Naive baseline MAPE: 24.6%
- Improvement over naive: 13.5%

Note: The short series (53 weeks, only 10 test points) limits forecast precision.
Holt-Winters was chosen over XGBoost specifically because gradient boosting
requires substantially more observations to generalize — using the right model
for the data size is the point.

## Stack
- Python, pandas, NumPy
- statsmodels (Holt-Winters)
- scikit-learn, XGBoost
- MLflow (experiment tracking)
- Tableau (dashboard)

## Files
```
data/
  retail_clean.csv          — cleaned transaction data
outputs/
  cohort_retention.csv      — monthly cohort retention matrix
  purchase_funnel.csv       — funnel stage counts and rates
  rfm_segments.csv          — per-customer RFM scores and segments
  trending_products.csv     — top 20 trending products by momentum
  weekly_revenue.csv        — weekly aggregated revenue, orders, customers
  forecast_full_series.csv  — actual vs fitted/forecast for full series
  revenue_forecast.csv      — test-set forecast vs actual
models/
  demand_model.joblib       — saved Holt-Winters model artifact
```

## How this maps to Fanatics Collectibles

| Fanatics need | CardPulse equivalent |
|---|---|
| User retention analysis | Cohort retention matrix |
| Purchase funnel analysis | 3-stage funnel (all/repeat/loyal) |
| Product trend detection | Revenue momentum scoring |
| Demand forecasting | Holt-Winters weekly forecast |
| Customer segmentation | RFM scoring + Champions/Potential/At Risk tiers |
| BI dashboard | Tableau dashboard (5 views) |
| Statistical rigor | MAPE vs naive baseline comparison, cohort sizing |
