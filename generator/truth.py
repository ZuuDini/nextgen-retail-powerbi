"""Builds the CLEAN tables — exactly what a correct Power Query cleanup should yield.

defects.py then damages copies of these to produce the raw "client exports".
expected_kpis.py computes the answer key from these clean tables.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import config as C


def build_stores() -> pd.DataFrame:
    rows, n = [], 1
    for region, cities in C.STORES.items():
        for city, state in cities:
            rows.append({
                "StoreCode": f"ST-{n:03d}",
                "StoreName": f"{city} #{n}",
                "City": city,
                "State": state,
                "Region": region,
            })
            n += 1
    return pd.DataFrame(rows)


def build_products(rng: np.random.Generator) -> pd.DataFrame:
    rows, n = [], 1
    for category, subs in C.CATALOG.items():
        for sub, (noun, (cmin, cmax), (mmin, mmax)) in subs.items():
            for i in range(C.PRODUCTS_PER_SUBCATEGORY):
                cost = round(float(rng.uniform(cmin, cmax)), 2)
                price = round(cost * float(rng.uniform(mmin, mmax)), 0) - 0.01
                brand = C.BRANDS[int(rng.integers(len(C.BRANDS)))]
                rows.append({
                    "ProductKey": f"P-{n:05d}",
                    "ProductName": f"{brand} {noun} {100 + i * 10}",
                    "Category": category,
                    "Subcategory": sub,
                    "Brand": brand,
                    "UnitCost": cost,
                    "ListPrice": round(price, 2),
                    # popularity weight used for basket picks (not exported)
                    "_pop": float(rng.lognormal(0.0, 0.6)),
                })
                n += 1
    return pd.DataFrame(rows)


def build_customers(rng: np.random.Generator, stores: pd.DataFrame) -> pd.DataFrame:
    segs = list(C.SEGMENTS)
    shares = np.array([C.SEGMENTS[s][0] for s in segs])
    seg = rng.choice(segs, size=C.N_CUSTOMERS, p=shares / shares.sum())
    home = rng.choice(stores["StoreCode"].to_numpy(), size=C.N_CUSTOMERS)
    store_by_code = stores.set_index("StoreCode")
    ages = np.clip(rng.normal(41, 13, C.N_CUSTOMERS).round(), 18, 85).astype(int)
    genders = rng.choice(["Female", "Male", "Non-binary"], size=C.N_CUSTOMERS,
                         p=[0.51, 0.46, 0.03])
    income = rng.choice(["<$50K", "$50-100K", "$100-150K", "$150K+"],
                        size=C.N_CUSTOMERS, p=[0.28, 0.38, 0.22, 0.12])
    signup_offsets = rng.integers(0, 365 * 6, C.N_CUSTOMERS)
    rows = []
    for i in range(C.N_CUSTOMERS):
        s = store_by_code.loc[home[i]]
        rows.append({
            "CustomerKey": f"C-{i + 1:05d}",
            "Segment": seg[i],
            "Age": int(ages[i]),
            "Gender": genders[i],
            "IncomeBand": income[i],
            "City": s["City"],
            "State": s["State"],
            "HomeStore": home[i],
            "SignupDate": date(2023, 12, 31) - timedelta(days=int(signup_offsets[i])),
        })
    return pd.DataFrame(rows)


def _random_date(rng: np.random.Generator, year: int) -> date:
    w = np.array(C.SEASONALITY)
    month = int(rng.choice(12, p=w / w.sum())) + 1
    day = int(rng.integers(1, calendar.monthrange(year, month)[1] + 1))
    return date(year, month, day)


def build_sales(rng: np.random.Generator, stores: pd.DataFrame,
                products: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    region_of = dict(zip(stores["StoreCode"], stores["Region"]))
    stores_in = stores.groupby("Region")["StoreCode"].apply(list).to_dict()
    pkeys = products["ProductKey"].to_numpy()
    price = dict(zip(products["ProductKey"], products["ListPrice"]))
    is_outdoor = (products["Category"] == "Outdoor").to_numpy()
    base_w = products["_pop"].to_numpy()
    base_p = base_w / base_w.sum()
    south_w = base_w * np.where(is_outdoor, C.SOUTH_2025_OUTDOOR_WEIGHT, 1.0)
    south_p = south_w / south_w.sum()
    outdoor_keys = set(products.loc[is_outdoor, "ProductKey"])

    lines, order_no = [], 1
    for cust in customers.itertuples(index=False):
        region = region_of[cust.HomeStore]
        for year in C.YEARS:
            lam = C.SEGMENTS[cust.Segment][1 if year == 2024 else 2]
            if year == 2025:
                lam *= C.GROWTH_2025
                if region == "South":
                    lam *= C.SOUTH_2025_ORDER_LIFT
            south_promo = year == 2025 and region == "South"
            for _ in range(int(rng.poisson(lam))):
                odate = _random_date(rng, year)
                online = rng.random() < C.ONLINE_SHARE
                if online or rng.random() < C.HOME_STORE_SHARE:
                    store = cust.HomeStore
                else:
                    store = str(rng.choice(stores_in[region]))
                ship = odate if not online else min(
                    odate + timedelta(days=int(rng.integers(1, 6))), C.END)
                n_lines = int(rng.choice([1, 2, 3, 4], p=[0.35, 0.35, 0.2, 0.1]))
                picks = rng.choice(pkeys, size=n_lines, replace=False,
                                   p=south_p if south_promo else base_p)
                for ln, pk in enumerate(picks, start=1):
                    qty = int(rng.choice([1, 2, 3], p=[0.7, 0.22, 0.08]))
                    if south_promo and pk in outdoor_keys:
                        disc = (int(rng.choice(C.SOUTH_2025_DISCOUNTS))
                                if rng.random() < C.SOUTH_2025_PROMO_SHARE else 0)
                    else:
                        disc = (int(rng.choice(C.BASE_DISCOUNTS))
                                if rng.random() < C.BASE_PROMO_SHARE else 0)
                    lines.append({
                        "OrderID": f"SO-{order_no:06d}", "LineNo": ln,
                        "OrderDate": odate, "ShipDate": ship,
                        "StoreCode": store, "ProductKey": pk,
                        "CustomerKey": cust.CustomerKey,
                        "Channel": "Online" if online else "In-Store",
                        "Quantity": qty, "UnitPrice": price[pk],
                        "DiscountPct": disc,
                    })
                    # returns: same order, negative qty, later date, no ship date
                    if rng.random() < C.RETURN_RATE:
                        rdate = odate + timedelta(days=int(rng.integers(3, 31)))
                        if rdate <= C.END:
                            lines.append({**lines[-1], "LineNo": ln + 100,
                                          "OrderDate": rdate, "ShipDate": None,
                                          "Quantity": -qty})
                order_no += 1

    sales = pd.DataFrame(lines)
    sales = sales.sort_values(["OrderDate", "OrderID", "LineNo"]).reset_index(drop=True)
    return sales


def build_inventory(rng: np.random.Generator, stores: pd.DataFrame,
                    products: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    """Month-end on-hand units per store x product, ~N months of that cell's demand."""
    region_of = dict(zip(stores["StoreCode"], stores["Region"]))
    s = sales[sales["Quantity"] > 0].copy()
    # smooth demand: average monthly units per store x product x year
    s["Year"] = pd.to_datetime(s["OrderDate"]).dt.year
    yearly = (s.groupby(["StoreCode", "ProductKey", "Year"])["Quantity"].sum() / 12)

    months = pd.period_range("2024-01", "2025-12", freq="M")
    rows = []
    for store in stores["StoreCode"]:
        mult_2025 = C.SOUTH_2025_COVER_MULT if region_of[store] == "South" else 1.0
        for pk in products["ProductKey"]:
            for m in months:
                avg = yearly.get((store, pk, m.year), 0.0)
                cover = C.BASE_COVER_MONTHS * (mult_2025 if m.year == 2025 else 1.0)
                noise = float(rng.uniform(0.8, 1.2))
                on_hand = int(round(avg * cover * noise)) + int(rng.integers(0, 3))
                rows.append({"SnapshotDate": m.to_timestamp(how="end").date(),
                             "StoreCode": store, "ProductKey": pk,
                             "OnHandUnits": on_hand})
    return pd.DataFrame(rows)


def build_targets(sales: pd.DataFrame, products: pd.DataFrame,
                  stores: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Monthly region targets: 2024 = actual-ish; 2025 = 2024 actual x 1.06 (pre-promo plan)."""
    region_of = dict(zip(stores["StoreCode"], stores["Region"]))
    s = sales.copy()
    s["Region"] = s["StoreCode"].map(region_of)
    s["Amount"] = s["Quantity"] * s["UnitPrice"] * (1 - s["DiscountPct"] / 100)
    s["Month"] = pd.to_datetime(s["OrderDate"]).dt.month
    s["Year"] = pd.to_datetime(s["OrderDate"]).dt.year
    a24 = s[s["Year"] == 2024].groupby(["Region", "Month"])["Amount"].sum()
    rows = []
    for (region, month), actual in a24.items():
        for year, mult in ((2024, float(rng.uniform(0.97, 1.04))), (2025, 1.06)):
            rows.append({"Region": region, "MonthStart": date(year, month, 1),
                         "TargetSales": float(round(actual * mult, -2))})
    return pd.DataFrame(rows).sort_values(["Region", "MonthStart"]).reset_index(drop=True)


def build_all(seed: int) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    stores = build_stores()
    products = build_products(rng)
    customers = build_customers(rng, stores)
    sales = build_sales(rng, stores, products, customers)
    inventory = build_inventory(rng, stores, products, sales)
    targets = build_targets(sales, products, stores, rng)
    return {"stores": stores, "products": products, "customers": customers,
            "sales": sales, "inventory": inventory, "targets": targets}
