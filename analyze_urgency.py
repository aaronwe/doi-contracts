#!/usr/bin/env python3
"""
Generate urgency investigation report for Trump II NPS no-bid contracts.

Reads nps_no_bid_contracts.csv + justifications_manifest.csv.
Produces: urgency_investigation.md

Usage:
    source .venv/bin/activate
    python analyze_urgency.py
"""

import os
from datetime import date

import pandas as pd

from config import INVESTIGATION_MD, MANIFEST_CSV
from urgency_utils import load_trump2_urg_awards


# ── Helpers ───────────────────────────────────────────────────────────────────

def truncate(text, max_len: int = 120) -> str:
    if not text or pd.isna(text):
        return ""
    text = str(text)
    return text[:max_len] + "…" if len(text) > max_len else text


def ja_status(row: pd.Series) -> str:
    if row.get("doc_local_path", ""):
        return "Downloaded"
    return "Link only"


def build_links_cell(row: pd.Series) -> str:
    parts = []
    usa = row.get("usaspending_url", "")
    sam_piid = row.get("sam_piid_url", "")
    sam_sol = row.get("sam_solicitation_url", "")
    if usa:
        parts.append(f"[USASpending]({usa})")
    if sam_piid:
        parts.append(f"[SAM (PIID)]({sam_piid})")
    if sam_sol:
        parts.append(f"[SAM (Solicitation)]({sam_sol})")
    return " ".join(parts)


# ── Report ────────────────────────────────────────────────────────────────────

_MANIFEST_COLS = [
    "award_id_piid", "usaspending_url", "sam_piid_url",
    "sam_solicitation_url", "doc_url", "doc_local_path",
]


def generate_report(awards: pd.DataFrame, manifest: pd.DataFrame) -> str:
    # Keep only the manifest columns we need to avoid duplicate column names after merge
    manifest_slim = manifest[[c for c in _MANIFEST_COLS if c in manifest.columns]].copy()
    merged = awards.merge(manifest_slim, on="award_id_piid", how="left")
    merged = merged.sort_values("total_obligation", ascending=False)

    # Fill NaN in manifest columns so string checks are safe (NaN is truthy in Python)
    for col in _MANIFEST_COLS:
        if col in merged.columns:
            merged[col] = merged[col].fillna("")

    today = date.today()
    days_window = (today - date(2025, 1, 20)).days
    total_dollars = merged["total_obligation"].sum()
    n_downloaded = (merged["doc_local_path"].fillna("") != "").sum()

    lines = [
        "# NPS Urgency Contract Investigation — Trump II",
        "",
        f"**Generated:** {today.isoformat()}",
        f"**Window:** 2025-01-20 through {today.isoformat()} ({days_window} days)",
        f"**Total URG contracts:** {len(merged)}",
        f"**Total obligated:** ${total_dollars:,.0f}",
        f"**J&A docs downloaded:** {n_downloaded} | **Link only:** {len(merged) - n_downloaded}",
        "",
        "All contracts used FAR 6.302-2 (URGENCY) justification. Sorted by dollar amount descending.",
        "",
        "| $ | PIID | Vendor | Description | Location | PSC | J&A | Links |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for _, row in merged.iterrows():
        city = str(row.get("primary_place_of_performance_city_name", "") or "").strip()
        state = str(row.get("primary_place_of_performance_state_code", "") or "").strip()
        location = f"{city}, {state}".strip(", ") if city or state else ""

        cells = [
            f"${row['total_obligation']:,.0f}",
            str(row.get("award_id_piid", "")),
            truncate(str(row.get("recipient_name", "")), 50),
            truncate(row.get("prime_award_base_transaction_description", "")),
            location,
            truncate(str(row.get("product_or_service_code_description", "")), 50),
            ja_status(row),
            build_links_cell(row),
        ]
        line = "| " + " | ".join(str(c).replace("|", "\\|") for c in cells) + " |"
        lines.append(line)

    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    awards = load_trump2_urg_awards()

    if os.path.exists(MANIFEST_CSV):
        # Read only the columns analyze_urgency.py needs; avoids duplicate column
        # names (e.g. recipient_name) after the merge in generate_report.
        manifest = pd.read_csv(
            MANIFEST_CSV, dtype=str,
            usecols=lambda c: c in _MANIFEST_COLS,
        )
    else:
        print(f"Warning: {MANIFEST_CSV} not found. Run fetch_justifications.py first.")
        manifest = pd.DataFrame(columns=_MANIFEST_COLS)

    report = generate_report(awards, manifest)

    with open(INVESTIGATION_MD, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Wrote {INVESTIGATION_MD}")
    print(f"  {len(awards)} contracts, ${awards['total_obligation'].sum():,.0f} total")


if __name__ == "__main__":
    main()
