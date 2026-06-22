"""Shared utilities for the urgency investigation pipeline."""

import pandas as pd
from config import OUTPUT_CSV, TRUMP2_START, URG_CODE


def load_trump2_urg_awards(master_csv: str = OUTPUT_CSV) -> pd.DataFrame:
    """
    Read master contracts CSV, filter to Trump II URG awards, return one row per award.

    Returns a DataFrame with:
      - all columns from the first transaction of each award
      - total_obligation: sum of federal_action_obligation across all transactions
      - first_action_date: earliest action_date as YYYY-MM-DD string
    """
    df = pd.read_csv(master_csv, dtype=str)
    df["action_date"] = pd.to_datetime(df["action_date"], errors="coerce")
    df["federal_action_obligation"] = pd.to_numeric(
        df["federal_action_obligation"], errors="coerce"
    ).fillna(0.0)

    trump2_start = pd.Timestamp(TRUMP2_START)
    mask = (df["action_date"] >= trump2_start) & (
        df["other_than_full_and_open_competition_code"] == URG_CODE
    )
    t2_urg = df[mask].copy()

    obligations = (
        t2_urg.groupby("contract_award_unique_key")["federal_action_obligation"]
        .sum()
        .reset_index()
        .rename(columns={"federal_action_obligation": "total_obligation"})
    )

    first_rows = (
        t2_urg.sort_values("action_date")
        .groupby("contract_award_unique_key")
        .first()
        .reset_index()
    )
    first_rows["first_action_date"] = first_rows["action_date"].dt.strftime("%Y-%m-%d")

    awards = first_rows.merge(obligations, on="contract_award_unique_key")
    return awards
