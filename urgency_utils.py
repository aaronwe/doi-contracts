"""Shared utilities for the urgency investigation pipeline."""

import pandas as pd
from config import NPS_OUTPUT_CSV, TRUMP2_START, URG_CODE


def load_trump2_urg_awards(master_csv: str = NPS_OUTPUT_CSV) -> pd.DataFrame:
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

    # F3: only count contracts whose first-ever transaction originates in Trump II
    first_dates = df.groupby("contract_award_unique_key")["action_date"].min()
    originated_in_t2 = first_dates[first_dates >= trump2_start].index

    is_urg = (
        (df["other_than_full_and_open_competition_code"] == URG_CODE) |
        (df["fair_opportunity_limited_sources_code"].fillna("") == URG_CODE)
    )
    mask = (
        (df["action_date"] >= trump2_start)
        & is_urg
        & df["contract_award_unique_key"].isin(originated_in_t2)
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
