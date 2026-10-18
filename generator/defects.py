"""Turns the clean tables into messy "client exports", one named defect at a time.

Every defect below is listed in docs/data-quality-log.md with how to detect it in
Power Query (column profiling) and how to fix it. Recoverable defects (formats,
duplicates, whitespace) are undone by the Power Query steps. Unrecoverable ones
(lost segment, impossible ages, blank or orphan inventory rows) have a documented
rule, and the CLEAN tables returned here already apply that rule, so the answer
key matches what a correct cleanup produces.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

from . import config as C

FIXED_TS = datetime(2026, 1, 5, 8, 0, 0)


def _workbook() -> Workbook:
    """Workbook with fixed metadata timestamps, so reruns produce identical cells."""
    wb = Workbook()
    wb.properties.created = wb.properties.modified = FIXED_TS
    wb.properties.creator = "legacy-erp-export"
    return wb

GHOST_STORE = "st099"  # closed warehouse still in the inventory feed
GHOST_MONTHS = ["2025-01", "2025-02", "2025-03"]


# ---------- customers.json -------------------------------------------------

def defect_customers(customers: pd.DataFrame, rng: np.random.Generator):
    """Null segments, impossible ages, inconsistent gender codes, nested JSON."""
    clean = customers.copy()
    n = len(clean)
    null_seg = rng.random(n) < C.NULL_SEGMENT_SHARE
    bad_age = rng.random(n) < C.CUSTOMER_BAD_AGE_SHARE
    clean.loc[null_seg, "Segment"] = "Unassigned"
    clean["Age"] = clean["Age"].astype("Int64")
    clean.loc[bad_age, "Age"] = pd.NA

    gender_variants = {"Female": ["Female", "F", "female"],
                       "Male": ["Male", "M", "male"],
                       "Non-binary": ["Non-binary", "NB"]}
    records = []
    for i, c in enumerate(customers.itertuples(index=False)):
        records.append({
            "customer_id": c.CustomerKey,
            "segment": None if null_seg[i] else c.Segment,
            "signup_date": c.SignupDate.isoformat(),
            "demographics": {
                "age": int(rng.choice([0, 7, 130, 999])) if bad_age[i] else c.Age,
                "gender": str(rng.choice(gender_variants[c.Gender])),
                "income_band": c.IncomeBand,
            },
            "address": {"city": c.City, "state": c.State, "home_store": c.HomeStore},
        })
    profile = {"customers": n, "null_segment": int(null_seg.sum()),
               "bad_age": int(bad_age.sum())}
    return clean, {"exported_at": "2026-01-05T08:00:00Z", "customers": records}, profile


# ---------- product_master.xlsx --------------------------------------------

def defect_products(products: pd.DataFrame, rng: np.random.Generator, path: Path):
    """Title rows above the header, merged Category cells, numeric IDs (zeros lost),
    trailing spaces in names."""
    wb = _workbook()
    ws = wb.active
    ws.title = "Products"
    ws["A1"] = "Client Retail Co. — Product Master Export"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = "Source: legacy ERP. Do not edit."
    headers = ["Product ID", "Product Name", "Category", "Subcategory", "Brand",
               "Unit Cost", "List Price"]
    ws.append([])  # row 3 blank
    ws.append(headers)  # row 4
    padded = 0
    start_row = 5
    for cat, block in products.groupby("Category", sort=False):
        first = start_row
        for j, p in enumerate(block.itertuples(index=False)):
            name = p.ProductName
            if rng.random() < 0.10:
                name += "   "
                padded += 1
            ws.append([int(p.ProductKey[2:]), name, cat if j == 0 else None,
                       p.Subcategory, p.Brand, p.UnitCost, p.ListPrice])
            start_row += 1
        ws.merge_cells(start_row=first, start_column=3, end_row=start_row - 1, end_column=3)
    wb.save(path)
    return {"products": len(products), "header_row": 4, "padded_names": padded,
            "merged_category_blocks": products["Category"].nunique()}


# ---------- regional_performance.xlsx --------------------------------------

REGION_VARIANTS = {
    "Northeast": ["Northeast", "NE", " north east"],
    "South": ["South", "SOUTH", "South "],
    "Midwest": ["Midwest", "Mid-West", "MW"],
    "West": ["West", "west", " West"],
}


def defect_regional(stores: pd.DataFrame, targets: pd.DataFrame,
                    rng: np.random.Generator, path: Path):
    """Region spelled many ways; targets in a wide month-per-column layout with a
    title row and a Total row."""
    wb = _workbook()
    ws = wb.active
    ws.title = "Stores"
    ws.append(["Store Code", "Store Name", "City", "State", "Region"])
    variants_used = set()
    for s in stores.itertuples(index=False):
        r = str(rng.choice(REGION_VARIANTS[s.Region]))
        variants_used.add(r)
        ws.append([s.StoreCode, s.StoreName, s.City, s.State, r])

    wt = wb.create_sheet("Monthly Targets")
    wt["A1"] = "Sales targets by region (USD)"
    wt["A1"].font = Font(bold=True)
    wt.append([])
    months = sorted(targets["MonthStart"].unique())
    wt.append(["Region"] + [m.strftime("%Y-%m") for m in months])  # row 3
    wide = targets.pivot(index="Region", columns="MonthStart", values="TargetSales")
    for region in C.STORES:
        label = REGION_VARIANTS[region][1]  # abbreviated spelling, e.g. "NE"
        wt.append([label] + [float(wide.loc[region, m]) for m in months])
    wt.append(["Total"] + [float(wide[m].sum()) for m in months])
    wb.save(path)
    return {"stores": len(stores), "region_spellings": len(variants_used),
            "target_header_row": 3, "target_month_columns": len(months),
            "target_rows_after_unpivot": len(targets)}


# ---------- sales_transactions_YYYY.csv ------------------------------------

def _fmt_date(d, year):
    if d is None or (isinstance(d, float) and np.isnan(d)) or pd.isna(d):
        return ""
    if year == 2024:
        return d.strftime("%m/%d/%Y")
    return d.strftime("%d-%b-%Y") if d >= C.ALT_DATE_FORMAT_FROM else d.isoformat()


def defect_sales(sales: pd.DataFrame, rng: np.random.Generator, out: Path):
    """2024: US dates, decimal discounts, TOTAL footer row.
    2025: ISO dates switching to dd-MMM-yyyy mid-year, '$1,234.50' prices,
    '15%' discounts, ~0.8% exact duplicate rows. Both: stray whitespace in StoreCode."""
    header = ["OrderID", "LineNo", "OrderDate", "ShipDate", "StoreCode",
              "ProductID", "CustomerID", "Channel", "Quantity", "UnitPrice",
              "DiscountPct"]
    profile = {}
    years = pd.to_datetime(sales["OrderDate"]).dt.year
    for year in C.YEARS:
        part = sales[years == year]
        rows, dupes, ws = [], 0, 0
        for r in part.itertuples(index=False):
            store = r.StoreCode
            if rng.random() < C.STORE_CODE_WHITESPACE_SHARE:
                store = store + " " if rng.random() < 0.5 else " " + store
                ws += 1
            if year == 2024:
                price, disc = f"{r.UnitPrice:.2f}", f"{r.DiscountPct / 100:.2f}"
            else:
                price, disc = f"${r.UnitPrice:,.2f}", f"{r.DiscountPct}%"
            row = [r.OrderID, r.LineNo, _fmt_date(r.OrderDate, year),
                   _fmt_date(r.ShipDate, year), store, r.ProductKey,
                   r.CustomerKey, r.Channel, r.Quantity, price, disc]
            rows.append(row)
            if year == 2025 and rng.random() < C.DUPLICATE_SHARE_2025:
                rows.append(list(row))
                dupes += 1
        if year == 2024:
            rows.append(["TOTAL", "", "", "", "", "", "", "",
                         int(part["Quantity"].sum()), "", ""])
        with open(out / f"sales_transactions_{year}.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        profile[str(year)] = {"raw_rows": len(rows), "duplicates": dupes,
                              "footer_rows": 1 if year == 2024 else 0,
                              "whitespace_store_codes": ws,
                              "clean_rows": len(part)}
    return profile


# ---------- inventory_snapshots.csv ----------------------------------------

def defect_inventory(inventory: pd.DataFrame, products: pd.DataFrame,
                     rng: np.random.Generator, path: Path):
    """Codes in another system's style (st001 / P00042), month as text, blank
    counts, and an orphan store that isn't in the store master."""
    blank = rng.random(len(inventory)) < C.INVENTORY_BLANK_SHARE
    clean = inventory.loc[~blank].reset_index(drop=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["month", "store", "sku", "on_hand"])
        for i, r in enumerate(inventory.itertuples(index=False)):
            w.writerow([r.SnapshotDate.strftime("%Y-%m"),
                        "st" + r.StoreCode[3:], "P" + r.ProductKey[2:],
                        "" if blank[i] else r.OnHandUnits])
        ghost = 0
        for m in GHOST_MONTHS:
            for pk in products["ProductKey"]:
                w.writerow([m, GHOST_STORE, "P" + pk[2:], int(rng.integers(0, 40))])
                ghost += 1
    profile = {"raw_rows": len(inventory) + ghost, "blank_on_hand": int(blank.sum()),
               "orphan_store_rows": ghost, "clean_rows": len(clean)}
    return clean, profile


def make_raw(truth: dict[str, pd.DataFrame], seed: int, out: Path):
    """Write every raw file; return (clean tables, raw profile)."""
    rng = np.random.default_rng(seed + 1)
    out.mkdir(parents=True, exist_ok=True)
    clean = {k: v.copy() for k, v in truth.items()}
    clean["products"] = clean["products"].drop(columns="_pop")
    profile = {}

    clean["customers"], doc, profile["customers"] = defect_customers(truth["customers"], rng)
    (out / "customers.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    profile["products"] = defect_products(clean["products"], rng, out / "product_master.xlsx")
    profile["regional"] = defect_regional(truth["stores"], truth["targets"], rng,
                                          out / "regional_performance.xlsx")
    profile["sales"] = defect_sales(truth["sales"], rng, out)
    clean["inventory"], profile["inventory"] = defect_inventory(
        truth["inventory"], truth["products"], rng, out / "inventory_snapshots.csv")
    return clean, profile
