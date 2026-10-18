# Data-quality log

Every problem found in the client's raw exports, how it was detected, what was done, and how many rows it touched. The counts are for seed 387 and come from `data/expected/raw_profile.json`. The tests fail if they drift.

**Detect with:** in Power Query, View > Column quality, Column distribution, Column profile. Set profiling to **"based on entire data set"** in the status bar, or it only looks at the first 1,000 rows and misses most of these.

## Sales transactions (`sales_transactions_2024.csv`, `sales_transactions_2025.csv`)

| # | Defect | How it showed up | Fix (query step) | Rows |
|---|---|---|---|---|
| S1 | Two files, one per year | Folder of exports | Folder.Files + combine, all columns kept as text (`FactSales` steps 1) | 29,202 + 32,160 raw |
| S2 | 2024 file ends with a `TOTAL` row | Column distribution on OrderID: one non-`SO-` value | Filter `OrderID <> "TOTAL"` (`RemovedFooter`) | 1 removed |
| S3 | 2025 export re-sent some lines | Column profile: distinct < count on a key-like column; Keep Duplicates shows exact copies | Remove duplicates on all columns (`RemovedDuplicates`) | 248 removed |
| S4 | Three date formats: `03/05/2024`, `2025-03-05`, `05-Jul-2025` (format changed at the July 2025 POS migration) | Changing type to Date with the default locale errors on roughly half the 2025 rows | `fxParseDate` tries each format in turn | all rows |
| S5 | Return lines have no ship date | Column quality: ShipDate has empty values, all on negative-quantity rows | Kept as null; ShipDate relationship is inactive anyway | 2,279 |
| S6 | Stray spaces around StoreCode (`"ST-004 "`) | Distinct count of StoreCode is above 20 | `fxStoreKey` keeps only the digits | 891 (2024) + 959 (2025) |
| S7 | 2025 prices are text: `"$1,234.50"` | Column type stays Text; type change to Decimal errors | Remove `$` and `,`, parse with `en-US` | 32,160 |
| S8 | Discount is `0.15` in 2024 and `"15%"` in 2025 | Column distribution shows both styles | One rule converts both to whole percent (15) | all rows |
| S9 | Returns are negative quantities | Column profile: Quantity min is below 0 | **Kept.** Net sales should go down when goods come back. Flagged with `IsReturn` | 2,279 |

Rows after cleanup: **61,113** (`61,362 - 1 footer - 248 duplicates`).

## Product master (`product_master.xlsx`)

| # | Defect | How it showed up | Fix | Rows |
|---|---|---|---|---|
| P1 | Title, note and blank row above the header | First rows of the sheet aren't data | Skip 3 rows, promote headers | 3 |
| P2 | Category was a merged cell | Category is null on all but the first row of each block | Fill Down | 236 filled |
| P3 | Product IDs became numbers (`42`, not `P-00042`) | Doesn't match the sales file; merge returns no matches | `fxProductKey` rebuilds `P-00042` | 240 |
| P4 | Trailing spaces in product names | Duplicate-looking names in visuals; length differs | Text.Trim | 23 |

## Regional performance (`regional_performance.xlsx`)

| # | Defect | How it showed up | Fix | Rows |
|---|---|---|---|---|
| R1 | 11 spellings of 4 regions (`NE`, `" north east"`, `Mid-West`, `MW`, `SOUTH`, ...) | Column distribution on Region shows 11 distinct values | `fxRegion` mapping. An unknown spelling is an error, not a new region | 20 stores |
| R2 | Targets sheet is wide: one column per month | 25 columns, 24 of them months | Unpivot other columns | 4 × 24 = 96 rows |
| R3 | Title + blank row above the targets header | First rows aren't data | Skip 2 rows, promote headers | 2 |
| R4 | `Total` row at the bottom of the targets | Would double every target | Filter it out | 1 |
| R5 | Targets use abbreviations (`NE`, `MW`) | Same as R1 | Same `fxRegion` function | 4 |

## Customers (`customers.json`)

| # | Defect | How it showed up | Fix | Rows |
|---|---|---|---|---|
| C1 | Nested JSON (`demographics`, `address` records) | Columns show `[Record]` | Expand the list into a table, then expand both records | 6,500 |
| C2 | Segment missing | Column quality: 6% empty | Replace null with `Unassigned`. The customers stay in because their sales are real | 387 |
| C3 | Impossible ages: 0, 7, 130, 999 | Column profile: min 0, max 999 | Set to null outside 16-100; AgeBand = `Unknown` | 63 |
| C4 | Gender coded 8 ways (`F`, `female`, `Female`, `M`, `NB`, ...) | Column distribution | Mapping to 3 values | all |

Note: 6,500 customers are in the file, but only **6,137** bought anything in 2024-2025. That's not a defect. The rest are dormant sign-ups, and they show up as a blank row if you count customers from DimCustomer instead of FactSales.

## Inventory snapshots (`inventory_snapshots.csv`)

| # | Defect | How it showed up | Fix | Rows |
|---|---|---|---|---|
| I1 | Store codes in a different style (`st001`) | Merge with DimStore finds no matches | `fxStoreKey` | all |
| I2 | SKUs in a different style (`P00042`) | Merge with DimProduct finds no matches | `fxProductKey` | all |
| I3 | Month is text (`2024-01`) | Not a date | Convert to the month-end date | all |
| I4 | Blank on-hand counts | Column quality: empty values | **Removed.** Blank means "not counted", not zero; replacing it with 0 would understate stock | 357 |
| I5 | Store `ST-099` isn't in the store master (a closed warehouse, Jan-Mar 2025) | `InventoryOrphanCheck` (left anti join) | Inner join to DimStore drops them | 720 |

Rows after cleanup: **114,843** (`115,920 - 357 - 720`).

## Rules applied, for the client to confirm

1. Net sales include returns, dated on the day the goods came back.
2. A blank stock count is excluded, not treated as zero.
3. Customers with a missing segment are reported as `Unassigned`. They are not dropped or guessed.
4. Inventory for stores outside the store master is excluded until the client says what ST-099 is.
