"""Generate the synthetic client exports and the answer key.

    .venv/bin/python -m generator.generate            # seed 387 -> data/
    .venv/bin/python -m generator.generate --seed 7 --out /tmp/x
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import config as C
from .defects import make_raw
from .expected_kpis import compute
from .truth import build_all

ROOT = Path(__file__).resolve().parent.parent


def run(seed: int, out: Path) -> dict:
    truth = build_all(seed)
    clean, profile = make_raw(truth, seed, out / "raw")
    kpis = compute(clean)
    (out / "expected").mkdir(parents=True, exist_ok=True)
    (out / "expected" / "kpis.json").write_text(json.dumps(kpis, indent=2) + "\n")
    (out / "expected" / "raw_profile.json").write_text(
        json.dumps({"seed": seed, **profile}, indent=2) + "\n")
    return {"kpis": kpis, "profile": profile, "clean": clean}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--out", type=Path, default=ROOT / "data")
    args = ap.parse_args()
    res = run(args.seed, args.out)
    k = res["kpis"]
    print(f"seed {args.seed} -> {args.out}")
    print(f"  FactSales rows: {k['Row Counts']['FactSales']:,}")
    print(f"  Total Sales (2 yrs): ${k['All Years']['Total Sales']:,.2f}")
    print(f"  2025 YoY: {k['By Year']['2025']['Sales YoY %']:.2%}")


if __name__ == "__main__":
    main()
