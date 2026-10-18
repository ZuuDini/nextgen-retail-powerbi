# Sales grew 8.5% last year. Was it healthy growth?

A Power BI engagement for a retail client: five messy exports from three systems turned into one clean star-schema model and an executive dashboard. It answers what the client asked (*sales performance, customer buying patterns, inventory turnover by region*) and the question they didn't ask: **where the growth came from, and what it cost.**

> **The data is synthetic.** A seeded Python generator (`generator/`) writes realistic exports with real-world defects planted on purpose, plus a business story for the analysis to find. That makes the project fully reproducible and publishable, and every number in the report can be checked against an answer key. No real company's data is used.

**Status:** data, cleaning scripts, model design, DAX and answer key are done. The report build is in progress (see [docs/build-guide.md](docs/build-guide.md)).

---

## The scenario

As a new analyst on a consulting firm's BI & Insights team, I was handed a retail client's raw exports:

| File | From | What was wrong with it |
|---|---|---|
| `sales_transactions_2024.csv`, `_2025.csv` | POS | 3 date formats, prices as `"$1,234.50"` text, 248 duplicate lines, a TOTAL row, two discount formats |
| `product_master.xlsx` | ERP | title rows above the header, merged category cells, product IDs that lost their leading zeros |
| `regional_performance.xlsx` | Finance | 11 spellings of 4 regions, targets in a wide month-per-column layout with a Total row |
| `customers.json` | CRM | nested records, 387 missing segments, impossible ages (0, 999), gender coded 8 ways |
| `inventory_snapshots.csv` | Warehouse | another system's key formats, blank counts, 720 rows for a store that doesn't exist |

All 27 issues, how each was detected and fixed, and the row counts are in [docs/data-quality-log.md](docs/data-quality-log.md).

## Method

1. **Power Query (M):**
   - A `DataFolder` parameter.
   - Four reusable functions (`fxStoreKey`, `fxProductKey`, `fxRegion`, `fxParseDate`) so three systems' key formats meet in one place.
   - Folder combine, unpivot, fill down, JSON expansion, and an anti-join data-quality query. Code is in [`powerquery/`](powerquery).
2. **Model:**
   - Star schema: 2 fact tables (sales lines, monthly inventory snapshots), 5 dimensions, a marked date table.
   - An inactive ship-date relationship.
   - A shared region dimension so targets and stores filter together.
   - Product and geography hierarchies.
3. **DAX:**
   - Time intelligence (YTD, PY, YoY, MoM, rolling 3 months), USERELATIONSHIP, and RANKX with a what-if Top N.
   - A field parameter, context transition (repeat customers), and semi-additive inventory (averaging snapshots, not summing them).
   - Conditional formatting measures. Code is in [`dax/measures.dax`](dax/measures.dax).
4. **Report:**
   - Executive overview, products, customers, regions & inventory, a drill-through store page, and a tooltip page.
   - Bookmarks and synced slicers.
   - An insights page with a decomposition tree, key influencers, anomaly detection and Q&A.
5. **Governance:** row-level security per regional manager, a published workspace, scheduled refresh, and publish to web.
6. **Trace every number:** `generator/expected_kpis.py` recomputes every measure in Python from the clean data ([`data/expected/kpis.json`](data/expected/kpis.json)), and every card in the report is checked against it. 15 tests prove the raw files clean back to exactly that answer key.

## Findings

| | 2024 | 2025 | |
|---|---|---|---|
| Company sales | $6.78M | $7.36M | **+8.5%** |
| South region sales | $1.78M | $2.40M | +34.7%, **27% over target** |
| Northeast + Midwest + West sales | $5.00M | $4.96M | −0.8%, all three missed target |
| South margin | 51.4% | 42.3% | −9.1 pts |
| South avg discount | 2.7% | 15.9% | |
| South average inventory (at cost) | $258K | $517K | **doubled** |
| South days of supply | 109 | 136 | others: ~112-114 |
| Loyalist orders | 4,745 | 4,125 | −13%; repeat rate 92.8% → 87.5% |

1. **All of the growth came from one region, and it was bought with discounts.** Without the South, sales fell 0.8%. The South's Outdoor promotions (25-40% off on most Outdoor lines) drove the units, and its margin fell from 51% to 42%.
2. **The promotion was stocked as if it would last.** South inventory doubled while its sales rose 35%. That's about 23 more days of stock than any other region, and cash sitting on shelves.
3. **The best customers are buying less often.** Loyalists, the highest-frequency segment, placed 13% fewer orders. Every other segment grew. Almost none of them left (31 of 1,159 didn't buy in 2025), so this is about frequency, not churn. It doesn't show in the company total, because the South promotion covers it up.

## Recommendation

- **Cap South Outdoor discounts at ~15%**, and measure whether the volume holds. At 2025 volume, every 5 points of discount recovered on South Outdoor is worth about $96K of margin, before any volume loss.
- **Stop replenishing South stock to the promotional run-rate.** Bring days of supply back to ~112 by working down the excess, not by marking it down further.
- **Run a Loyalist frequency campaign** before the Q4 peak. They haven't left, they visit less. Give them a reason to come back sooner that isn't a discount.
- **Trade-off:** pulling discounts back will cost the South some 2025-style revenue. The goal is margin dollars and cash, not the top line.

## With the client's real data, I'd next

- Run a price-elasticity test on Outdoor, with discount depth by store as a natural experiment.
- Join marketing spend, to see whether the South's promotion paid for its own advertising.
- Move from monthly snapshots to daily stock, and add stock-outs (lost sales are invisible here).
- Build a churn model for the Loyalist segment to replace the repeat-rate proxy.

## Reproduce it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m generator.generate      # writes data/raw + data/expected (seed 387)
.venv/bin/python -m pytest                   # 15 tests: determinism, defects present, cleanup = answer key
```

Then follow [docs/build-guide.md](docs/build-guide.md) in Power BI Desktop. The report is saved as a Power BI Project (`report/*.pbip`), so the model, measures and queries are plain text in git.

## Repo layout

```
generator/   seeded data generator, defects, Python mirror of the cleanup, answer key
data/raw/    the "client exports" Power Query reads
data/expected/  kpis.json (answer key), raw_profile.json (defect counts)
powerquery/  every query and function in M
dax/         every measure, calculated table and RLS rule
report/      the Power BI Project (.pbip)
docs/        build guide, data-quality log, screenshots
tests/       pytest suite
```

*Built as the portfolio project for Per Scholas 387.1 (Data Analyst in Power BI) and PL-300 prep.*
