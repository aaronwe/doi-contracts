#!/usr/bin/env python3
"""
Compare NPS no-bid contracts across four administrations for matching time windows.

Reads: nps_no_bid_contracts.csv  (produced by fetch_contracts.py)
Writes: admin_comparison.csv

The comparison window for each administration = the first N days of that
administration, where N = days Trump II has been in office as of today.

Metrics reported per administration:
  - window_start / window_end
  - days_in_window
  - unique_contract_count   unique contract_award_unique_key values where
                             action_date falls in the window
  - total_obligated         sum of federal_action_obligation for all
                             transactions in the window ($ millions)
  - median_obligation       median per-transaction obligation in the window
  - top_justification_code  most common other_than_full_and_open_competition_code
  - top_justification       human-readable label for the above

Usage:
    python compare_admins.py
"""

import sys
import os
import pandas as pd
from datetime import date

from config import ADMINISTRATIONS, OUTPUT_CSV, COMPARISON_CSV

TRUMP_II_INAUGURATION = date(2025, 1, 20)


def load_contracts(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run fetch_contracts.py first.")
        sys.exit(1)

    df = pd.read_csv(csv_path, dtype=str, low_memory=False)
    df["action_date"] = pd.to_datetime(df["action_date"], errors="coerce")
    df["federal_action_obligation"] = pd.to_numeric(
        df["federal_action_obligation"], errors="coerce"
    )
    return df


def compute_window(inauguration: date, days: int):
    """Return (start, end) dates for an administration window of `days` length."""
    start = inauguration
    end = inauguration + pd.Timedelta(days=days - 1)
    return pd.Timestamp(start), pd.Timestamp(end)


def summarize_window(df: pd.DataFrame, start, end) -> dict:
    mask = (df["action_date"] >= start) & (df["action_date"] <= end)
    window_df = df[mask]

    if window_df.empty:
        return {
            "unique_contract_count": 0,
            "total_obligated_millions": 0.0,
            "median_obligation": 0.0,
            "top_justification_code": None,
            "top_justification": None,
            "transaction_count": 0,
        }

    total_obligated = window_df["federal_action_obligation"].sum()
    median_obl = window_df["federal_action_obligation"].median()

    # Top justification by frequency
    justification_counts = (
        window_df["other_than_full_and_open_competition_code"]
        .dropna()
        .value_counts()
    )
    if not justification_counts.empty:
        top_code = justification_counts.index[0]
        # Get human-readable label from the most recent matching row
        label_match = window_df[
            window_df["other_than_full_and_open_competition_code"] == top_code
        ]["other_than_full_and_open_competition"].dropna()
        top_label = label_match.iloc[0] if not label_match.empty else top_code
    else:
        top_code = None
        top_label = None

    return {
        "unique_contract_count": window_df["contract_award_unique_key"].nunique(),
        "total_obligated_millions": round(total_obligated / 1_000_000, 3),
        "median_obligation": round(float(median_obl), 2),
        "top_justification_code": top_code,
        "top_justification": top_label,
        "transaction_count": len(window_df),
    }


def main():
    today = date.today()
    days_elapsed = (today - TRUMP_II_INAUGURATION).days + 1

    print(f"Trump II in office: {days_elapsed} days (as of {today})")
    print(f"Comparing first {days_elapsed} days for each administration.\n")

    df = load_contracts(OUTPUT_CSV)
    print(f"Loaded {len(df):,} transactions, {df['contract_award_unique_key'].nunique():,} unique awards\n")

    rows = []
    for admin in ADMINISTRATIONS:
        start, end = compute_window(admin["inauguration"], days_elapsed)
        stats = summarize_window(df, start, end)
        row = {
            "administration": admin["name"],
            "window_start": start.date().isoformat(),
            "window_end": end.date().isoformat(),
            "days_in_window": days_elapsed,
            **stats,
        }
        rows.append(row)

    comparison = pd.DataFrame(rows)
    comparison.to_csv(COMPARISON_CSV, index=False)

    # Pretty-print to console
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 120)
    pd.set_option("display.float_format", lambda x: f"{x:,.3f}")

    print("=" * 80)
    print(f"NPS No-Bid Contracts: First {days_elapsed} Days by Administration")
    print("=" * 80)

    display_cols = [
        "administration", "window_start", "window_end",
        "unique_contract_count", "total_obligated_millions",
        "median_obligation", "top_justification_code",
    ]
    print(comparison[display_cols].to_string(index=False))
    print()

    # Highlight Trump II vs each prior administration
    trump_ii = comparison[comparison["administration"] == "Trump II"].iloc[0]
    print("Comparison vs Trump II:")
    for _, row in comparison[comparison["administration"] != "Trump II"].iterrows():
        count_ratio = (
            trump_ii["unique_contract_count"] / row["unique_contract_count"]
            if row["unique_contract_count"] > 0 else float("inf")
        )
        oblig_ratio = (
            trump_ii["total_obligated_millions"] / row["total_obligated_millions"]
            if row["total_obligated_millions"] > 0 else float("inf")
        )
        print(
            f"  vs {row['administration']}: "
            f"{count_ratio:.1f}x contracts, "
            f"{oblig_ratio:.1f}x obligations"
        )

    print(f"\nFull results written to {COMPARISON_CSV}")


if __name__ == "__main__":
    main()
