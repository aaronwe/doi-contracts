#!/usr/bin/env python3
"""
Generate doi_viz.html from doi_no_bid_contracts.csv.

Reads doi_no_bid_contracts.csv, applies the same exclusions as compare_admins.py,
aggregates per-agency and per-justification-bucket obligations, and injects the
result into doi_viz_template.html to produce doi_viz.html.

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
)

TRUMP_II_INAUGURATION = TRUMP2_START
EXCLUDE_JUSTIFICATION_CODES = {"OTH", "UT", "ONE", "UNQ"}
OTHER_THRESHOLD_DOLLARS = 100_000

AGENCY_COLORS = {
    "National Park Service":          "#E24B4A",
    "Bureau of Land Management":      "#EF9F27",
    "Bureau of Indian Affairs":       "#4A90D9",
    "U.S. Fish and Wildlife Service": "#5BAD6F",
    "U.S. Geological Survey":         "#9B59B6",
    "Other DOI bureaus":              "#888780",
}
FALLBACK_COLORS = ["#1A7CBF", "#C45E00", "#2E7D32", "#6A1B9A", "#00695C"]

JUST_URGENCY  = "Urgency (FAR 6.302-2)"
JUST_FOLLOWON = "Follow-on contract"
JUST_OTHER    = "Other"
JUST_ORDER    = [JUST_URGENCY, JUST_FOLLOWON, JUST_OTHER]

# Codes in other_than_full_and_open_competition_code that indicate follow-on work.
# Inspected value_counts() on NPS data (proxy for DOI): FOO does not appear in
# other_than_full_and_open_competition_code, but is kept here to support the
# classification code path (and FOO does appear in fair_opportunity_limited_sources_code).
FOLLOW_ON_OTF_CODES      = {"FOO"}
# Codes in fair_opportunity_limited_sources_code that indicate follow-on work.
# FOO = Follow-On Action Following Competitive Initial Action (4 occurrences in NPS data).
FOLLOW_ON_FAIR_OPP_CODES = {"FOO"}

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
    return df


def classify_justification(otf: str, fair: str) -> str:
    if otf == "URG" or fair == "URG":
        return JUST_URGENCY
    if otf in FOLLOW_ON_OTF_CODES or fair in FOLLOW_ON_FAIR_OPP_CODES:
        return JUST_FOLLOWON
    return JUST_OTHER


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


def aggregate_agency_breakdown(
    df: pd.DataFrame, admin_names: list, windows: dict
) -> dict:
    df = df.copy()
    otf  = df["other_than_full_and_open_competition_code"].fillna("").astype(str).str.strip()
    fair = df["fair_opportunity_limited_sources_code"].fillna("").astype(str).str.strip()
    # Replace literal "nan" strings that survive dtype=str reads
    otf  = otf.where(otf  != "nan", "")
    fair = fair.where(fair != "nan", "")
    df["_just"] = [classify_justification(o, f) for o, f in zip(otf, fair)]
    result = {}
    for agency, grp in df.groupby("awarding_sub_agency_name"):
        buckets = {b: [] for b in JUST_ORDER}
        for name in admin_names:
            start, end = windows[name]
            mask = (grp["action_date"] >= start) & (grp["action_date"] <= end)
            win = grp[mask]
            for bucket in JUST_ORDER:
                val = float(win[win["_just"] == bucket]["federal_action_obligation"].sum())
                buckets[bucket].append(round(val / 1_000_000, 3))
        result[agency] = buckets
    return result


def build_data(df: pd.DataFrame) -> dict:
    today = date.today()
    days_elapsed = (today - TRUMP_II_INAUGURATION).days + 1
    admin_map = {a["name"]: a["inauguration"] for a in ADMINISTRATIONS}
    windows = {name: compute_window(admin_map[name], days_elapsed) for name in VIZ_ADMIN_NAMES}

    doi_obligations = aggregate_doi_obligations(df, VIZ_ADMIN_NAMES, windows)
    all_breakdown   = aggregate_agency_breakdown(df, VIZ_ADMIN_NAMES, windows)

    # visible_agencies = agencies that were NOT rolled into "Other DOI bureaus" by the rollup.
    # doi_obligations is already post-rollup, so its keys are exactly the visible set.
    visible_agencies = set(doi_obligations.keys()) - {"Other DOI bureaus"}
    agency_breakdown = {a: all_breakdown[a] for a in visible_agencies if a in all_breakdown}

    if "Other DOI bureaus" in doi_obligations:
        other_bd = {b: [0.0] * len(VIZ_ADMIN_NAMES) for b in JUST_ORDER}
        for a, buckets in all_breakdown.items():
            if a not in visible_agencies:
                for b in JUST_ORDER:
                    for i, v in enumerate(buckets[b]):
                        other_bd[b][i] = round(other_bd[b][i] + v, 3)
        agency_breakdown["Other DOI bureaus"] = other_bd

    fb_idx = 0
    agency_colors = {}
    for agency in doi_obligations:
        if agency in AGENCY_COLORS:
            agency_colors[agency] = AGENCY_COLORS[agency]
        else:
            agency_colors[agency] = FALLBACK_COLORS[fb_idx % len(FALLBACK_COLORS)]
            fb_idx += 1

    return {
        "days_in_window": days_elapsed,
        "window_label":   f"First {days_elapsed} days",
        "administrations": VIZ_ADMIN_NAMES,
        "agency_colors":   agency_colors,
        "doi_obligations": doi_obligations,
        "agency_breakdown": agency_breakdown,
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
    print(f"Loaded {len(df):,} DOI transactions, {df['contract_award_unique_key'].nunique():,} unique awards")
    data = build_data(df)

    agencies = list(data["doi_obligations"].keys())
    print(f"Agencies in viz ({len(agencies)}): {agencies}")
    for name in VIZ_ADMIN_NAMES:
        idx = VIZ_ADMIN_NAMES.index(name)
        total = sum(v[idx] for v in data["doi_obligations"].values())
        print(f"  {name}: ${total:.1f}M total")

    inject_and_write(data, DOI_VIZ_TEMPLATE, DOI_VIZ_OUTPUT)
    print(f"\nWrote {DOI_VIZ_OUTPUT}")


if __name__ == "__main__":
    main()
