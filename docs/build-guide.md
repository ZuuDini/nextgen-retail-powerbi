# Build guide

Five sittings, about 20 hours. Each milestone ends with a check you can verify and a commit. The answer key for every number is `data/expected/kpis.json`. If Power BI disagrees with it, the model is wrong, so fix it before moving on.

`powerquery/*.pq` and `dax/measures.dax` hold the finished code. **Build each step with the UI first**, then compare with the file (Home > Advanced Editor). Pasting the file is how you recover from a stuck step. It is not how you learn the step, and the PL-300 tests the UI.

---

## Milestone 0: Windows VM and Power BI Desktop (one-time)

1. **VM.** Use Parallels Desktop, VMware Fusion (free for personal use), or UTM, running Windows 11 ARM. Give it 8 GB RAM and 4 cores if the Mac can spare them.
   - Microsoft doesn't officially support Power BI Desktop on ARM, but it normally runs under Windows' x64 emulation. If it won't install, the fallback is a lab PC.
2. **Power BI Desktop.** Install from the Microsoft Store. The Store version updates itself.
3. **Shared folder.** Share `~/Projects/nextgen-retail-powerbi` into the VM:
   - Parallels: it appears as `\\Mac\Home\Projects\nextgen-retail-powerbi\`.
   - VMware: `\\vmware-host\Shared Folders\...`.
   - UTM: shared folders are awkward. Copy `data/raw/` into the VM instead, and copy the saved project back out.
4. **Options** (File > Options and settings > Options):
   - *Preview features*: turn on **Power BI Project (.pbip) save option** and **Store semantic model using TMDL format**, if they're listed. Newer builds have them on by default.
   - *Current file > Data Load*: **uncheck Auto date/time.** You'll build a proper date table, and auto date/time adds a hidden table for every date column.
   - *Regional settings*: English (United States).
5. **Save** the empty report as a project: File > Save as > `report/NextGenRetail.pbip`.

---

## Milestone 1: Get and clean the data (~4 hrs)

**Parameter first.** Home > Transform data > Manage parameters > New:
- `DataFolder`, Text, value = the path to `data\raw\` **ending in a backslash**.
- Every query below builds its file path from it. To point the report at another folder (or at SharePoint, see Milestone 5), you change one value.

**Functions.** Home > New source > Blank query > Advanced Editor, paste each `fx*.pq`, and name the query to match: `fxStoreKey`, `fxProductKey`, `fxRegion`, `fxParseDate`. Test each one with *Invoke*:
- `fxStoreKey(" st004 ")` → `ST-004`
- `fxProductKey(42)` → `P-00042`
- `fxRegion("Mid-West")` → `Midwest`
- `fxParseDate("05-Jul-2025")` → 7/5/2025

**Profiling.** Turn on View > Column quality / distribution / profile. Click the status-bar text and switch to **"Column profiling based on entire data set"**. Most of the defects are invisible in the first 1,000 rows.

Build the queries in this order, checking the row count (bottom-left of the editor) at each checkpoint.

### FactSales
Get data > Folder > `data\raw` > **Combine & Transform**.
- **Do this before anything else:** delete every auto-generated *Changed Type* step, in both the combined query and *Transform Sample File*. Power BI guesses types from the first file. The guess is wrong for the second file, and the bad rows become errors that get silently dropped. Keep everything as text until it's clean.
- Filter to file names starting with `sales_transactions_`.

| After step | Rows | What you just fixed (DQ log #) |
|---|---|---|
| Combined | 61,362 | S1 |
| Removed footer (`OrderID <> "TOTAL"`) | 61,361 | S2 |
| Removed duplicates (select all columns > Remove duplicates) | **61,113** | S3 |

Then:
- Parse dates (Add Column > Invoke custom function `fxParseDate`, or Transform with the function).
- Clean keys with `fxStoreKey` and `fxProductKey`.
- Price: Replace values `$` → nothing and `,` → nothing, then change type *Using locale* English (US).
- Discount: one rule for both styles (see the .pq).
- Add Column > Custom: `LineAmount` = `[Quantity] * [UnitPrice] * (1 - [DiscountPct]/100)`. Add `IsReturn` too.
- **Check:** no errors in any column (Column quality shows 0% error), and Quantity min is -3.

### DimProduct
Excel workbook > `product_master.xlsx` > *Products*. Remove top 3 rows, Use first row as headers, Fill Down on Category, Trim on Product Name, `fxProductKey` on Product ID.
**Check:** 240 rows; Category has 4 distinct values and 0 empty.

### DimStore, DimRegion, RegionTargets
- `regional_performance.xlsx` > *Stores*: promote headers, then run `fxRegion` on Region.
  **Check:** 20 rows; Region goes from 11 distinct values to 4.
- **DimRegion:** right-click DimStore > *Reference*. Keep Region, Remove duplicates. **4 rows.**
- *Monthly Targets*: remove top 2 rows, promote headers, filter out `Total`, select Region > **Unpivot other columns**, `fxRegion`, then a MonthStart date from the month text.
  **Check: 96 rows.**

### DimCustomer
JSON > `customers.json`. Click `customers` *List* > **To Table** > expand the record, then expand `demographics` and `address`.
- Replace null in Segment with `Unassigned` (387 of them).
- Null the impossible ages (63).
- Map the gender codes.
- Add the conditional column **AgeBand**.
**Check:** 6,500 rows; Segment has 5 values; Age min ≥ 18.

### FactInventory and InventoryOrphanCheck
CSV > `inventory_snapshots.csv`. **115,920** raw rows.
- Filter out blank `on_hand` → **115,563**.
- Month text → month-end date.
- `fxStoreKey` / `fxProductKey`.
- Merge with DimStore on StoreCode. Do it twice:
  - **Left anti** in a separate query, `InventoryOrphanCheck`. Expect 720 rows, all `ST-099`. Right-click it > uncheck *Enable load*.
  - **Inner** in FactInventory → **114,843**.

**Close & Apply.** Then:
- Report view > Table view: the row counts should match `"Row Counts"` in kpis.json.
- Save, then `git add -A && git commit -m "M1: Power Query cleanup"` (from the Mac terminal).

---

## Milestone 2: Model (~3 hrs)

**Date table.** Modeling > New table > paste `DimDate` from measures.dax.
- Table tools > **Mark as date table** > Date.
- Sort `Month` by `MonthNum`.
- Build a hierarchy: Year > Quarter > Month > Date.

**Relationships** (Model view; all single direction, one-to-many):

| From (many) | To (one) | Active |
|---|---|---|
| FactSales[OrderDate] | DimDate[Date] | ✅ |
| FactSales[ShipDate] | DimDate[Date] | ❌ inactive (used by `Sales by Ship Date`) |
| FactSales[ProductKey] | DimProduct[ProductKey] | ✅ |
| FactSales[StoreCode] | DimStore[StoreCode] | ✅ |
| FactSales[CustomerKey] | DimCustomer[CustomerKey] | ✅ |
| FactInventory[SnapshotDate] | DimDate[Date] | ✅ |
| FactInventory[ProductKey] | DimProduct[ProductKey] | ✅ |
| FactInventory[StoreCode] | DimStore[StoreCode] | ✅ |
| DimStore[Region] | DimRegion[Region] | ✅ |
| RegionTargets[Region] | DimRegion[Region] | ✅ |
| RegionTargets[MonthStart] | DimDate[Date] | ✅ |

Why **DimRegion**: targets are set per region, not per store. Both DimStore and RegionTargets need a common one-side to filter from. Slice target visuals by `DimRegion[Region]`. `DimStore[Region]` doesn't reach the targets.

**Tidy the model.** This is what reviewers look at:
- **Hierarchies:**
  - Product: Category > Subcategory > ProductName
  - Geography: DimStore Region > State > City > StoreName
- **Hide:** the key columns on the fact tables, `LineAmount`, and `UnitCost` (users should go through the measures). Hide `HomeStore`.
- **Data category:** City → City, State → State or Province (this drives the map).
- **Default summarization:** set to *Don't summarize* for UnitCost, ListPrice, Age, LineNo.
- **Measures table:** Home > Enter data, an empty table called `_Measures`. All measures go here.

**Check:**
- Model view looks like a star (two facts in the middle, dimensions around them) with no many-to-many and no bidirectional arrows.
- Screenshot it to `docs/screenshots/model.png`, then commit.

---

## Milestone 3: DAX, and checking every number (~4 hrs)

Write the measures in `dax/measures.dax` in the order they appear: Sales, Time intelligence, Targets, Inventory, Ranking, Logic.
- Create the **Top N** numeric parameter and the **Metric Selector** field parameter from Modeling > New parameter.
- Set format strings as you go.

**The check.** Build a scratch page called `QA` with a table: rows = DimDate[Year], values = every measure. Add a second table by DimRegion[Region] × Year. Compare against kpis.json:

| Check | Expected |
|---|---|
| Total Sales, both years | $14,134,578.87 |
| Total Sales 2025 · YoY | $7,355,947.69 · 8.5% |
| Orders · Customers (both years) | 28,594 · 6,137 |
| Return Rate % 2025 | 4.1% |
| South 2025: Sales · YoY · vs Target | $2,395,337.61 · 34.7% · +27.1% |
| South 2025: Margin % · Avg Discount % | 42.3% · 15.9% |
| South 2025: Inventory Turnover · Days of Supply | 2.68 · 136.4 |
| Midwest 2025: Turnover · Days of Supply | 3.21 · 113.8 |
| Loyalist Repeat Rate % 2024 → 2025 | 92.8% → 87.5% |
| #1 product 2025 | Voltara Grill 290 · $318,147.17 |

The rest is in kpis.json (`By Region and Year`, `By Segment and Year`, `By Category and Year`).

**When a number is off**, find the cause before changing the measure:
- Customers too high → you counted from DimCustomer, not FactSales.
- Targets doubled → the Total row survived.
- Inventory 12× too big → you summed snapshots instead of averaging them.
- Region totals right but targets blank → you sliced by DimStore[Region].

Keep the QA page (hide it) and commit.

---

## Milestone 4: Report pages (~5 hrs)

Pick a theme (View > Themes, or import a JSON theme) and use it everywhere. Lay out the pages on a 1280×720 canvas.

1. **Executive Overview**
   - Cards: Total Sales, YoY %, Margin %, Orders, AOV, Repeat Rate %.
   - Line chart by YearMonth with the **Metric Selector** as Y.
   - Filled or bubble map by City sized by Total Sales.
   - Bar of Sales vs Target % by DimRegion with the Margin Color rule.
   - Slicers: Year, Region, Channel.
   - Title bound to `Page Title`.
2. **Products**
   - Matrix on the Product hierarchy (drill down with +), with Total Sales, Margin %, Avg Discount %. Conditional formatting: data bars on sales, background colour from `Margin Color`.
   - Top N bar chart driven by the Top N slider.
3. **Customers**
   - Segment × Year clustered columns for Repeat Rate %.
   - AgeBand and IncomeBand bars.
   - A small table: Customers, Orders, AOV by Segment.
4. **Regions & Inventory**
   - Turnover and Days of Supply by Region × Year.
   - Avg Inventory Value vs Total Sales combo chart by month.
   - Sell-Through % gauge.
5. **Store detail** (drill-through)
   - Drill-through field = DimStore[StoreName].
   - KPIs plus that store's top products.
   - Right-click any store anywhere → Drill through.
6. **Tooltip page**
   - Page information > Allow use as tooltip, canvas *Tooltip* size.
   - Mini trend + Margin %. Attach it to the map's tooltip.

Then add:
- **Bookmarks** on page 1: "2025 South view" vs "All regions", with a button for each.
- Sync slicers across pages 1-4 (View > Sync slicers).
- Edit interactions so the map filters, and doesn't highlight, the line chart.

**Check:**
- Click through every slicer and drill. No visual shows (Blank) where a number belongs.
- Screenshot each page into `docs/screenshots/` and commit.

---

## Milestone 5: Insights, security, Service (~4 hrs)

**Insights page.**
- **Decomposition tree:** Analyze `Total Sales`, explain by Region > Category > Subcategory > Channel. Pin the path South > Outdoor > Grills.
- **Key influencers:** Analyze `FactSales[DiscountPct]` (increase), explain by DimStore[Region], DimProduct[Category], FactSales[Channel], DimCustomer[Segment]. It should surface *Region is South* and *Category is Outdoor*. Read the bottom-segments tab too.
- **Anomaly detection:** line chart of Total Sales by DimDate[Date] (daily) > Analytics pane > Find anomalies. Explain one spike in a text box.
- **Q&A visual:** add synonyms in the model (`revenue` → Total Sales, `area` → Region) and try "total sales by region 2025".

**Row-level security.**
- Modeling > Manage roles. Create the four static roles in measures.dax.
- Modeling > **View as** > South Manager: every page should show South only, and the targets bar has one bar.
- Stretch: the dynamic `USERPRINCIPALNAME()` role.

**Publish (needs a work or school Microsoft account; the free Fabric trial works).**
1. Home > Publish > a new workspace `NextGen Retail`.
2. Semantic model settings:
   - Local files need an **on-premises data gateway (personal mode)** running in the VM before a scheduled refresh works.
   - The cloud alternative (deck slide 27): put `data/raw` in a SharePoint document library and swap the source in each query to `SharePoint.Files("https://<tenant>.sharepoint.com/sites/<site>", [ApiVersion = 15])`, filtered to the folder. No gateway needed.
   - Pro allows 8 scheduled refreshes a day; Premium Per User allows 48. Set 2 a day.
3. Security: assign yourself to *South Manager* and test with *Test as role*.
4. Workspace roles: know the difference between Admin, Member, Contributor and Viewer (it's on the exam).
5. File > Embed report > **Publish to web** for the public portfolio link. The data is synthetic, so a public link is fine. Your tenant admin may have it switched off. If so, export to PDF (File > Export) and record a 2-minute Loom instead.

**Finish.**
- Fill in the README's *Findings* with what *your* report shows, plus the public link or PDF.
- Commit.
- Push to GitHub once the README is honest about what's done.
