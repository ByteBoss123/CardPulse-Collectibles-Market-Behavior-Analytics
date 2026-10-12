# CardPulse: Customer Behavior and Demand Analytics for an Online Retailer

Retention, segmentation, product momentum and demand forecasting, the core product-analytics questions for a
marketplace. Built with a collectibles marketplace in mind, but the data is a UK online giftware retailer: no
public collectibles transaction data exists, and this is the closest real, customer-level e-commerce log.

**Data.** UCI Online Retail (Chen, 2015): 541,909 transaction lines, Dec 2010 to Dec 2011, fetched and checksum-
verified by `data/download.sh`. After removing cancellations, rows without a customer id and non-positive
quantities or prices: **397,884 lines, 4,338 customers, £8.91M revenue**.

## Results (`outputs/summary.json`)

| Question | Answer |
|---|---|
| Who comes back? | Month-1 retention **23.7%** (customer-weighted across monthly cohorts; 21.5% simple average), month-3 26.9%. Cells falling in the 9-day December 2011 month are excluded so they don't read as churn |
| How concentrated is revenue? | Top 20% of customers drive **74.6%** of revenue |
| Repeat behavior | 65.6% of customers ordered twice or more (2,845); 25.7% five or more (1,114) |
| Segments (RFM quartiles) | Champions: 1,319 customers, **73% of revenue**. At-risk (valuable but lapsing): 910 customers, 16% of revenue, the main win-back target |
| What's trending? | 9 of the top 20 "momentum" products (last 90 days vs prior 90) are Christmas items, and most of the rest are hot-water bottles and hand warmers. With one year of data, **momentum here is seasonality**; a real trend signal needs year-over-year comparison |
| Can we forecast weekly revenue? | Rolling-origin test, 4 weeks ahead from 13 origins: damped Holt **21.8% MAPE**, last-week naive 21.4%, **4-week average 17.6%**. The simplest baseline wins; 52 weeks is too short for a seasonal model to learn anything |

## What changed in the October 2026 rebuild

The repo previously held only a zip of outputs, with no code. This version is a single reproducible pipeline,
and rerunning it changed three conclusions:

- **The forecast result reversed.** The earlier README reported Holt-Winters beating a naive forecast by 13.5% on
  one 10-week test window that ended with a partial week. Across 13 rolling origins, with partial weeks removed,
  it loses to a 4-week average.
- **Retention is now defined.** The earlier 20.6% month-1 figure had no stated weighting and included the partial
  final month; both versions are now reported.
- **Trending products are labeled as seasonal**, with a Christmas-excluded list in
  `outputs/trending_products_ex_christmas.csv`.

The earlier Looker Studio PDF was removed: it showed a "System Error" panel and the superseded numbers.

## Run

```
pip install -r requirements.txt
bash data/download.sh
python src/pipeline.py     # about 30 seconds; writes outputs/
```
