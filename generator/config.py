"""Fixed reference data and tuning knobs for the synthetic retail client.

Everything here is invented. Store cities are real US cities so the map
visual works; brands and products are made up.
"""

from datetime import date

DEFAULT_SEED = 387  # Per Scholas course 387.1

START = date(2024, 1, 1)
END = date(2025, 12, 31)
YEARS = (2024, 2025)

N_CUSTOMERS = 6500

# region -> list of (city, state)
STORES = {
    "Northeast": [("New York", "NY"), ("Brooklyn", "NY"), ("Newark", "NJ"),
                  ("Boston", "MA"), ("Philadelphia", "PA")],
    "South": [("Houston", "TX"), ("Austin", "TX"), ("Atlanta", "GA"),
              ("Miami", "FL"), ("Charlotte", "NC")],
    "Midwest": [("Chicago", "IL"), ("Columbus", "OH"), ("Detroit", "MI"),
                ("Minneapolis", "MN"), ("St. Louis", "MO")],
    "West": [("Los Angeles", "CA"), ("San Diego", "CA"), ("Seattle", "WA"),
             ("Denver", "CO"), ("Phoenix", "AZ")],
}

# category -> subcategory -> (noun, cost range, markup range)
CATALOG = {
    "Outdoor": {
        "Camping": ("Tent", (40, 220), (1.8, 2.4)),
        "Hiking": ("Pack", (25, 140), (1.9, 2.5)),
        "Grills": ("Grill", (80, 700), (1.6, 2.1)),
    },
    "Home": {
        "Kitchen": ("Cookware Set", (15, 120), (2.0, 2.8)),
        "Bedding": ("Duvet", (20, 90), (2.2, 3.0)),
        "Decor": ("Lamp", (10, 70), (2.4, 3.2)),
    },
    "Electronics": {
        "Audio": ("Headphones", (25, 180), (1.4, 1.9)),
        "Smart Home": ("Hub", (20, 110), (1.5, 2.0)),
        "Accessories": ("Charger", (5, 30), (2.5, 3.5)),
    },
    "Apparel": {
        "Men's": ("Jacket", (18, 90), (2.2, 3.0)),
        "Women's": ("Coat", (20, 110), (2.2, 3.0)),
        "Footwear": ("Sneaker", (22, 80), (2.0, 2.6)),
    },
}
PRODUCTS_PER_SUBCATEGORY = 20
BRANDS = ["Northpeak", "Trailmark", "Hearthline", "Voltara", "Loomcraft",
          "Strideway", "Cedarbay", "Lumenox"]

# segment -> (share of customers, mean orders per year 2024, 2025)
SEGMENTS = {
    "Loyalist": (0.20, 4.0, 3.0),      # planted: 2025 frequency drops
    "Premium": (0.15, 2.6, 2.7),
    "Value Seeker": (0.35, 2.0, 2.1),
    "Occasional": (0.30, 0.8, 0.85),
}
NULL_SEGMENT_SHARE = 0.06  # raw export lost the segment for these customers

# Monthly seasonality (Jan..Dec)
SEASONALITY = [0.80, 0.75, 0.90, 0.95, 1.00, 1.05,
               1.00, 1.00, 0.95, 1.00, 1.30, 1.60]

ONLINE_SHARE = 0.25
HOME_STORE_SHARE = 0.85
RETURN_RATE = 0.04
BASE_PROMO_SHARE = 0.18          # share of lines with a promo discount
BASE_DISCOUNTS = [10, 15, 20]    # percent

# Planted story: South region, 2025 — deep Outdoor promotions and over-ordering
SOUTH_2025_ORDER_LIFT = 1.30     # more trips from promo traffic
SOUTH_2025_OUTDOOR_WEIGHT = 2.2  # Outdoor share of basket rises
SOUTH_2025_PROMO_SHARE = 0.70    # share of Outdoor lines discounted
SOUTH_2025_DISCOUNTS = [25, 30, 35, 40]
SOUTH_2025_COVER_MULT = 1.7      # months of stock on hand vs. other regions

BASE_COVER_MONTHS = 2.0          # typical on-hand = ~2 months of demand
GROWTH_2025 = 1.07               # baseline order growth everywhere else

# Raw-export defect rates
DUPLICATE_SHARE_2025 = 0.008
ALT_DATE_FORMAT_FROM = date(2025, 7, 1)  # POS migration changed the date format
STORE_CODE_WHITESPACE_SHARE = 0.03
INVENTORY_BLANK_SHARE = 0.003
CUSTOMER_BAD_AGE_SHARE = 0.01
