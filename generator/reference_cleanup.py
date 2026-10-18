"""Python mirror of the Power Query cleanup in powerquery/*.pq.

It exists only so tests can prove that following the documented cleaning rules on
data/raw/ gives back exactly the clean tables behind the answer key. Each step is
commented with the .pq query and Applied Step it mirrors.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

REGION_MAP = {"NORTHEAST": "Northeast", "NE": "Northeast", "SOUTH": "South",
              "MIDWEST": "Midwest", "MW": "Midwest", "WEST": "West"}
GENDER_MAP = {"F": "Female", "FEMALE": "Female", "M": "Male", "MALE": "Male",
              "NB": "Non-binary", "NON-BINARY": "Non-binary"}


def fx_store_key(v) -> str:            # fxStoreKey.pq
    return "ST-" + re.sub(r"\D", "", str(v)).zfill(3)


def fx_product_key(v) -> str:          # fxProductKey.pq
    return "P-" + re.sub(r"\D", "", str(v)).zfill(5)


def fx_region(v) -> str:               # fxRegion.pq
    return REGION_MAP[re.sub(r"[\s-]", "", str(v)).upper()]


def fx_parse_date(v):                  # fxParseDate.pq: try each known format
    if v is None or str(v).strip() == "":
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(str(v).strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unparsed date {v!r}")


def clean_sales(raw: Path) -> pd.DataFrame:           # FactSales.pq
    files = sorted(raw.glob("sales_transactions_*.csv"))
    df = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False) for f in files],
                   ignore_index=True)                 # Combine Files (all text)
    df = df[df["OrderID"] != "TOTAL"]                 # Removed footer row
    df = df.drop_duplicates()                         # Removed Duplicates
    out = pd.DataFrame({
        "OrderID": df["OrderID"],
        "LineNo": df["LineNo"].astype(int),
        "OrderDate": df["OrderDate"].map(fx_parse_date),
        "ShipDate": df["ShipDate"].map(fx_parse_date),
        "StoreCode": df["StoreCode"].map(fx_store_key),   # also trims
        "ProductKey": df["ProductID"].map(fx_product_key),
        "CustomerKey": df["CustomerID"],
        "Channel": df["Channel"],
        "Quantity": df["Quantity"].astype(int),
        "UnitPrice": df["UnitPrice"].str.replace(r"[$,]", "", regex=True).astype(float),
        # "15%" -> 15 ; "0.15" -> 15
        "DiscountPct": df["DiscountPct"].map(
            lambda s: round(float(s[:-1])) if s.endswith("%") else round(float(s) * 100)),
    })
    return out.sort_values(["OrderDate", "OrderID", "LineNo"]).reset_index(drop=True)


def clean_products(raw: Path) -> pd.DataFrame:        # DimProduct.pq
    df = pd.read_excel(raw / "product_master.xlsx", sheet_name="Products", header=3)
    df["Category"] = df["Category"].ffill()           # Filled Down (merged cells)
    return pd.DataFrame({
        "ProductKey": df["Product ID"].map(fx_product_key),
        "ProductName": df["Product Name"].str.strip(),
        "Category": df["Category"], "Subcategory": df["Subcategory"],
        "Brand": df["Brand"], "UnitCost": df["Unit Cost"].astype(float),
        "ListPrice": df["List Price"].astype(float),
    })


def clean_stores(raw: Path) -> pd.DataFrame:          # DimStore.pq
    df = pd.read_excel(raw / "regional_performance.xlsx", sheet_name="Stores")
    return pd.DataFrame({
        "StoreCode": df["Store Code"].map(fx_store_key),
        "StoreName": df["Store Name"], "City": df["City"], "State": df["State"],
        "Region": df["Region"].map(fx_region),
    })


def clean_targets(raw: Path) -> pd.DataFrame:         # RegionTargets.pq
    df = pd.read_excel(raw / "regional_performance.xlsx",
                       sheet_name="Monthly Targets", header=2)
    df = df[df["Region"] != "Total"]                  # Removed Total row
    long = df.melt(id_vars="Region", var_name="Month", value_name="TargetSales")  # Unpivot
    long["Region"] = long["Region"].map(fx_region)
    long["MonthStart"] = long["Month"].map(lambda m: datetime.strptime(m + "-01", "%Y-%m-%d").date())
    return (long[["Region", "MonthStart", "TargetSales"]]
            .sort_values(["Region", "MonthStart"]).reset_index(drop=True))


def clean_customers(raw: Path) -> pd.DataFrame:       # DimCustomer.pq
    doc = json.loads((raw / "customers.json").read_text(encoding="utf-8"))
    rows = []
    for c in doc["customers"]:                        # Expanded records
        age = c["demographics"]["age"]
        rows.append({
            "CustomerKey": c["customer_id"],
            "Segment": c["segment"] or "Unassigned",  # Replaced null
            "Age": age if 16 <= age <= 100 else pd.NA,  # impossible ages -> null
            "Gender": GENDER_MAP[c["demographics"]["gender"].upper()],
            "IncomeBand": c["demographics"]["income_band"],
            "City": c["address"]["city"], "State": c["address"]["state"],
            "HomeStore": c["address"]["home_store"],
            "SignupDate": datetime.strptime(c["signup_date"], "%Y-%m-%d").date(),
        })
    df = pd.DataFrame(rows)
    df["Age"] = df["Age"].astype("Int64")
    return df


def clean_inventory(raw: Path, stores: pd.DataFrame) -> pd.DataFrame:  # FactInventory.pq
    df = pd.read_csv(raw / "inventory_snapshots.csv", dtype=str, keep_default_na=False)
    df = df[df["on_hand"] != ""]                      # Removed blank counts
    out = pd.DataFrame({
        "SnapshotDate": df["month"].map(            # end of month
            lambda m: (pd.Period(m, "M").to_timestamp(how="end")).date()),
        "StoreCode": df["store"].map(fx_store_key),
        "ProductKey": df["sku"].map(fx_product_key),
        "OnHandUnits": df["on_hand"].astype(int),
    })
    out = out[out["StoreCode"].isin(stores["StoreCode"])]  # Inner merge drops orphans
    return out.reset_index(drop=True)


def clean_all(raw: Path) -> dict[str, pd.DataFrame]:
    stores = clean_stores(raw)
    return {"stores": stores, "products": clean_products(raw),
            "customers": clean_customers(raw), "sales": clean_sales(raw),
            "inventory": clean_inventory(raw, stores), "targets": clean_targets(raw)}
