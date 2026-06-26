#!/usr/bin/env python3
"""
Generate doi_viz.html from doi_no_bid_contracts.csv.

Reads doi_no_bid_contracts.csv, filters to urgency-only (FAR 6.302-2) contracts,
aggregates per-agency obligations, builds a flat contract list, and injects both
into doi_viz_template.html to produce doi_viz.html.

Usage:
    python build_doi_viz.py
"""

import json
import os
import sys
import pandas as pd
from datetime import date

from config import (
    DOI_OUTPUT_CSV,
    ADMINISTRATIONS,
    IDV_SOLE_SOURCE_FAIR_OPP_CODES,
    TRUMP2_START,
    URG_CODE,
)

TRUMP_II_INAUGURATION = TRUMP2_START
EXCLUDE_JUSTIFICATION_CODES = {"OTH", "UT", "ONE", "UNQ"}
EXCLUDE_AGENCIES = {"Departmental Offices"}
OTHER_THRESHOLD_DOLLARS = 100_000

AGENCY_COLORS = {
    "National Park Service":                                "#78b43c",  # CWP green
    "Bureau of Land Management":                            "#4398b5",  # CWP blue-4
    "Bureau of Indian Affairs and Bureau of Indian Education": "#d2781e",  # CWP orange
    "U.S. Fish and Wildlife Service":                       "#96782d",  # CWP gold
    "U.S. Geological Survey":                               "#63c5d8",  # CWP blue-6
    "Bureau of Reclamation":                                "#5a87a5",  # CWP blue
    "Departmental Offices":                                 "#d77a28",  # CWP orange-2
    "Other DOI bureaus":                                    "#9a9590",  # CWP mid-gray
}
FALLBACK_COLORS = ["#84bb41", "#6789a3", "#d77a28", "#998139", "#a1aa4e"]

AGENCY_SHORT = {
    "National Park Service":                                   "NPS",
    "Bureau of Land Management":                               "BLM",
    "Bureau of Indian Affairs and Bureau of Indian Education": "BIA/BIE",
    "U.S. Fish and Wildlife Service":                          "FWS",
    "U.S. Geological Survey":                                  "USGS",
    "Bureau of Reclamation":                                   "BOR",
    "Bureau of Ocean Energy Management":                       "BOEM",
    "Office of Surface Mining, Reclamation and Enforcement":   "OSMRE",
    "Bureau of Safety and Environmental Enforcement":          "BSEE",
}

VIZ_ADMIN_NAMES = ["Trump I", "Biden", "Trump II"]

DOI_VIZ_TEMPLATE = "doi_viz_template.html"
DOI_VIZ_OUTPUT   = "doi_viz.html"
INJECTION_MARKER = "/* __DOI_DATA__ */null/* end */"


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
    exclude_mask = df["other_than_full_and_open_competition_code"].isin(
        EXCLUDE_JUSTIFICATION_CODES
    )
    df = df[~exclude_mask | is_idv]
    if "fair_opportunity_limited_sources_code" in df.columns:
        df = df[df["fair_opportunity_limited_sources_code"].fillna("") != "FAIR"]
    df = df[~df["awarding_sub_agency_name"].isin(EXCLUDE_AGENCIES)]

    # Urgency-only: keep rows where OTF code or fair_opp code is URG
    is_urg = (
        (df["other_than_full_and_open_competition_code"] == URG_CODE) |
        (df["fair_opportunity_limited_sources_code"].fillna("") == URG_CODE)
    )
    return df[is_urg].copy()


def compute_window(inauguration: date, days: int):
    start = pd.Timestamp(inauguration)
    end = start + pd.Timedelta(days=days - 1)
    return start, end


def aggregate_doi_obligations(
    df: pd.DataFrame, admin_names: list, windows: dict
) -> dict:
    raw = {}
    for agency, grp in df.groupby("awarding_sub_agency_name"):
        vals = []
        for name in admin_names:
            start, end = windows[name]
            mask = (grp["action_date"] >= start) & (grp["action_date"] <= end)
            vals.append(round(float(grp[mask]["federal_action_obligation"].sum()) / 1_000_000, 3))
        raw[agency] = vals

    trump_ii_idx = admin_names.index("Trump II") if "Trump II" in admin_names else 0
    other_vals = [0.0] * len(admin_names)
    to_roll = [
        a for a, vals in raw.items()
        if sum(abs(v) for v in vals) * 1_000_000 < OTHER_THRESHOLD_DOLLARS
    ]
    for a in to_roll:
        for i, v in enumerate(raw.pop(a)):
            other_vals[i] = round(other_vals[i] + v, 3)
    if any(v != 0 for v in other_vals):
        raw["Other DOI bureaus"] = other_vals

    def sort_key(item):
        name, vals = item
        return float("-inf") if name == "Other DOI bureaus" else vals[trump_ii_idx]

    return dict(sorted(raw.items(), key=sort_key, reverse=True))


def _clean_str(val) -> str:
    s = str(val or "").strip()
    return "" if s == "nan" else s


def build_contracts_table(
    df: pd.DataFrame, admin_names: list, windows: dict
) -> list:
    contracts = []
    for admin_name in admin_names:
        start, end = windows[admin_name]
        window_mask = (df["action_date"] >= start) & (df["action_date"] <= end)
        window_df   = df[window_mask]

        # Determine which awards truly originated within this window by checking
        # the first action date across ALL transactions for each award, not just
        # those in the window (pre-window modifications would otherwise be invisible).
        all_first_dates = df.groupby("contract_award_unique_key")["action_date"].min()
        originated = all_first_dates[all_first_dates >= start].index
        # Then restrict to transactions that fall within the window
        award_df = window_df[window_df["contract_award_unique_key"].isin(originated)]

        obligations = (
            award_df.groupby("contract_award_unique_key")["federal_action_obligation"].sum()
        )
        first_rows = (
            award_df.sort_values("action_date")
            .groupby("contract_award_unique_key")
            .first()
        )
        for key, row in first_rows.iterrows():
            full_name = row["awarding_sub_agency_name"]
            desc = (
                _clean_str(row.get("transaction_description"))
                or _clean_str(row.get("prime_award_base_transaction_description"))
            )
            contracts.append({
                "piid":         row["award_id_piid"],
                "vendor":       row["recipient_name"],
                "description":  desc,
                "agency":       full_name,
                "agency_short": AGENCY_SHORT.get(full_name, full_name[:12]),
                "state":        str(row.get("primary_place_of_performance_state_code") or ""),
                "date":         row["action_date"].strftime("%Y-%m-%d"),
                "amount":       round(float(obligations.get(key, 0)) / 1_000_000, 4),
                "url":          f"https://www.usaspending.gov/award/{key}/",
                "admin":        admin_name,
            })

    return sorted(contracts, key=lambda x: x["amount"], reverse=True)


def build_data(df: pd.DataFrame) -> dict:
    today = date.today()
    days_elapsed = (today - TRUMP_II_INAUGURATION).days + 1
    admin_map = {a["name"]: a["inauguration"] for a in ADMINISTRATIONS}
    windows = {name: compute_window(admin_map[name], days_elapsed) for name in VIZ_ADMIN_NAMES}

    doi_obligations = aggregate_doi_obligations(df, VIZ_ADMIN_NAMES, windows)
    contracts       = build_contracts_table(df, VIZ_ADMIN_NAMES, windows)

    fb_idx = 0
    agency_colors = {}
    for agency in doi_obligations:
        if agency in AGENCY_COLORS:
            agency_colors[agency] = AGENCY_COLORS[agency]
        else:
            agency_colors[agency] = FALLBACK_COLORS[fb_idx % len(FALLBACK_COLORS)]
            fb_idx += 1

    return {
        "days_in_window":  days_elapsed,
        "window_label":    f"First {days_elapsed} days",
        "administrations": VIZ_ADMIN_NAMES,
        "agency_colors":   agency_colors,
        "doi_obligations": doi_obligations,
        "contracts":       contracts,
    }


def inject_and_write(data: dict, template_path: str, output_path: str) -> None:
    with open(template_path, encoding="utf-8") as f:
        html = f.read()
    if INJECTION_MARKER not in html:
        raise ValueError(f"Injection marker '{INJECTION_MARKER}' not found in {template_path}")
    html = html.replace(INJECTION_MARKER, json.dumps(data, ensure_ascii=False))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    df = load_contracts(DOI_OUTPUT_CSV)
    print(f"Loaded {len(df):,} DOI urgency transactions, {df['contract_award_unique_key'].nunique():,} unique awards")
    data = build_data(df)

    agencies = list(data["doi_obligations"].keys())
    print(f"Agencies in viz ({len(agencies)}): {agencies}")
    for name in VIZ_ADMIN_NAMES:
        idx = VIZ_ADMIN_NAMES.index(name)
        total = sum(v[idx] for v in data["doi_obligations"].values())
        print(f"  {name}: ${total:.1f}M urgency total")
    print(f"  Contracts in table: {len(data['contracts'])}")

    inject_and_write(data, DOI_VIZ_TEMPLATE, DOI_VIZ_OUTPUT)
    print(f"\nWrote {DOI_VIZ_OUTPUT}")


if __name__ == "__main__":
    main()
