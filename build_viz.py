#!/usr/bin/env python3
"""
Generate viz.html from nps_no_bid_contracts.csv.

Reads nps_no_bid_contracts.csv, filters to urgency-only (FAR 6.302-2),
computes per-administration stats for the current Trump II window, and
injects the data into viz_template.html to produce viz.html.

Usage:
    python build_viz.py
"""

import json
import os
import sys
import pandas as pd
from datetime import date

from config import (
    NPS_OUTPUT_CSV,
    ADMINISTRATIONS,
    IDV_SOLE_SOURCE_FAIR_OPP_CODES,
    TRUMP2_START,
    URG_CODE,
)

EXCLUDE_JUSTIFICATION_CODES = {"OTH", "UT", "ONE", "UNQ"}
VIZ_ADMIN_NAMES = ["Trump I", "Biden", "Trump II"]

VIZ_TEMPLATE = "viz_template.html"
VIZ_OUTPUT   = "viz.html"
INJECTION_MARKER = "/* __VIZ_DATA__ */null/* end */"


def load_contracts(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run fetch_contracts.py first.")
        sys.exit(1)
    df = pd.read_csv(csv_path, dtype=str, low_memory=False)
    df["action_date"] = pd.to_datetime(df["action_date"], errors="coerce")
    df["federal_action_obligation"] = pd.to_numeric(
        df["federal_action_obligation"], errors="coerce"
    )
    if "fair_opportunity_limited_sources_code" in df.columns:
        is_idv = df["fair_opportunity_limited_sources_code"].fillna("").isin(
            IDV_SOLE_SOURCE_FAIR_OPP_CODES
        )
    else:
        is_idv = pd.Series(False, index=df.index)
    excl_mask = df["other_than_full_and_open_competition_code"].isin(
        EXCLUDE_JUSTIFICATION_CODES
    )
    df = df[~excl_mask | is_idv]
    if "fair_opportunity_limited_sources_code" in df.columns:
        df = df[df["fair_opportunity_limited_sources_code"].fillna("") != "FAIR"]

    is_urg = (
        (df["other_than_full_and_open_competition_code"] == URG_CODE) |
        (df["fair_opportunity_limited_sources_code"].fillna("") == URG_CODE)
    )
    return df[is_urg].copy()


def build_data(df: pd.DataFrame) -> dict:
    today = date.today()
    days = (today - TRUMP2_START).days + 1

    admin_map = {a["name"]: a["inauguration"] for a in ADMINISTRATIONS}
    all_first_dates = df.groupby("contract_award_unique_key")["action_date"].min()

    admins = []
    for name in VIZ_ADMIN_NAMES:
        inaug = admin_map[name]
        start = pd.Timestamp(inaug)
        end   = start + pd.Timedelta(days=days - 1)

        window = df[(df["action_date"] >= start) & (df["action_date"] <= end)]
        originated = all_first_dates[
            (all_first_dates >= start) & (all_first_dates <= end)
        ].index
        award_df = window[window["contract_award_unique_key"].isin(originated)]

        obligations = award_df.groupby("contract_award_unique_key")[
            "federal_action_obligation"
        ].sum()

        total_m = round(float(obligations.sum()) / 1_000_000, 4)
        count   = len(obligations)
        admins.append({"name": name, "total_m": total_m, "count": count})

    return {"days": days, "admins": admins}


def inject_and_write(data: dict, template_path: str, output_path: str) -> None:
    with open(template_path, encoding="utf-8") as f:
        html = f.read()
    if INJECTION_MARKER not in html:
        raise ValueError(f"Injection marker not found in {template_path}")
    html = html.replace(INJECTION_MARKER, json.dumps(data, ensure_ascii=False))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    df = load_contracts(NPS_OUTPUT_CSV)
    print(f"Loaded {len(df):,} NPS urgency transactions")
    data = build_data(df)
    print(f"Window: first {data['days']} days")
    for a in data["admins"]:
        print(f"  {a['name']}: ${a['total_m']:.3f}M, {a['count']} awards")
    inject_and_write(data, VIZ_TEMPLATE, VIZ_OUTPUT)
    print(f"Wrote {VIZ_OUTPUT}")


if __name__ == "__main__":
    main()
