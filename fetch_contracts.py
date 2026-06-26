#!/usr/bin/env python3
"""
Fetch all DOI other-than-full-and-open (no-bid) contracts from USASpending.gov.

Produces:
  doi_no_bid_contracts.csv — all DOI bureaus, one row per FPDS transaction.
  nps_no_bid_contracts.csv — NPS subset derived from the DOI download.

Filtered to extent_competed_code in {B, C}.
Covers Obama I inauguration (2009-01-20) through today.

Re-running is safe: downloaded year ZIPs are cached in downloads/ as
doi_contracts_YYYY.zip and reused. If you have old nps_contracts_YYYY.zip
files from a prior run, delete them — they are no longer used.

Usage:
    pip install -r requirements.txt
    python fetch_contracts.py
"""

import os
import sys
import time
import zipfile
import io
import requests
import pandas as pd
from datetime import date

from config import (
    API_BASE,
    NPS_SUBTIER_NAME,
    DOI_TOPTIER_NAME,
    CONTRACT_AWARD_TYPES,
    NO_BID_CODES,
    IDV_SOLE_SOURCE_FAIR_OPP_CODES,
    DATA_START_DATE,
    DOI_OUTPUT_CSV,
    NPS_OUTPUT_CSV,
    DOWNLOADS_DIR,
    KEEP_COLUMNS,
)

POLL_INTERVAL_SECS = 5
MAX_POLL_ATTEMPTS = 240  # 20-minute ceiling per year


def _post_with_retry(url: str, payload: dict) -> dict:
    for attempt in range(1, 4):
        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if attempt == 3:
                raise
            wait = 2 ** attempt
            print(f"  request error ({type(e).__name__}), retrying in {wait}s...")
            time.sleep(wait)


def _build_download_payload(start_date: date, end_date: date) -> dict:
    return {
        "filters": {
            "prime_award_types": CONTRACT_AWARD_TYPES,
            "agencies": [
                {
                    "type": "awarding",
                    "tier": "toptier",
                    "name": DOI_TOPTIER_NAME,
                }
            ],
            "date_type": "action_date",
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        },
        "file_format": "csv",
    }


def derive_nps_subset(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["awarding_sub_agency_name"] == NPS_SUBTIER_NAME].copy()


def request_download(start_date: date, end_date: date) -> dict:
    payload = _build_download_payload(start_date, end_date)
    return _post_with_retry(f"{API_BASE}/bulk_download/awards/", payload)


def poll_until_done(file_name: str) -> str:
    """Poll until the async download job finishes. Returns the file_url."""
    status_url = f"{API_BASE}/download/status"
    for _ in range(MAX_POLL_ATTEMPTS):
        resp = requests.get(status_url, params={"file_name": file_name}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        status = data["status"]
        if status == "finished":
            print()  # newline after \r updates
            return data["file_url"]
        if status == "failed":
            raise RuntimeError(f"Download failed: {data.get('message')}")
        print(f"  waiting... {data.get('seconds_elapsed', '?')}s elapsed", end="\r", flush=True)
        time.sleep(POLL_INTERVAL_SECS)
    raise TimeoutError(f"Download timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECS}s")


def stream_zip_to_disk(file_url: str, zip_path: str):
    with requests.get(file_url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)


def read_and_filter_zip(zip_path: str) -> pd.DataFrame:
    """Extract the CSV from a ZIP, keep only no-bid rows and needed columns.

    Inclusion logic:
      (a) extent_competed_code in {B, C} AND fair_opportunity_limited_sources_code != "FAIR"
          → traditional no-bid contracts; FAIR exclusion removes GSA orders that were
            actually competed among schedule holders (Finding 2)
      (b) fair_opportunity_limited_sources_code in IDV_SOLE_SOURCE_FAIR_OPP_CODES
          → sole-source task orders under competed IDVs/GSA Schedules whose parent
            contract inherited an A/D extent_competed_code (Finding 1)
    """
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csv_names:
            raise ValueError(f"No CSV in {zip_path}")
        with zf.open(csv_names[0]) as f:
            df = pd.read_csv(
                io.TextIOWrapper(f, encoding="utf-8-sig"),
                dtype=str,
                low_memory=False,
            )

    bc_mask = df["extent_competed_code"].isin(NO_BID_CODES)

    if "fair_opportunity_limited_sources_code" in df.columns:
        fair_opp = df["fair_opportunity_limited_sources_code"].fillna("")
        not_fair_mask = fair_opp != "FAIR"
        idv_sole_source_mask = fair_opp.isin(IDV_SOLE_SOURCE_FAIR_OPP_CODES)
        df = df[(bc_mask & not_fair_mask) | idv_sole_source_mask].copy()
    else:
        df = df[bc_mask].copy()

    available = [c for c in KEEP_COLUMNS if c in df.columns]
    missing = set(KEEP_COLUMNS) - set(available)
    if missing:
        print(f"  note: columns absent in this year's data: {sorted(missing)}")
    return df[available]


def year_chunks(start: date, end: date):
    """Yield (start, end) pairs spanning at most one calendar year each."""
    current = start
    while current <= end:
        year_end = date(current.year, 12, 31)
        yield current, min(year_end, end)
        current = date(current.year + 1, 1, 1)


def main():
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    today = date.today()
    chunks = list(year_chunks(DATA_START_DATE, today))

    all_frames = []
    for chunk_start, chunk_end in chunks:
        year = chunk_start.year
        zip_path = os.path.join(DOWNLOADS_DIR, f"doi_contracts_{year}.zip")

        if os.path.exists(zip_path) and year != today.year:
            print(f"[{year}] using cached ZIP")
        else:
            print(f"[{year}] requesting {chunk_start} → {chunk_end}...")
            job = request_download(chunk_start, chunk_end)
            file_name = job["file_name"]
            print(f"  job: {file_name}")
            file_url = poll_until_done(file_name)
            print(f"  complete, downloading...")
            stream_zip_to_disk(file_url, zip_path)
            size_mb = os.path.getsize(zip_path) / 1_048_576
            print(f"  saved {zip_path} ({size_mb:.1f} MB)")

        df = read_and_filter_zip(zip_path)
        print(f"  {len(df):,} no-bid transactions")
        all_frames.append(df)

    if not all_frames:
        print("No data fetched.")
        sys.exit(1)

    combined = pd.concat(all_frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["contract_transaction_unique_key"])

    combined["action_date"] = pd.to_datetime(combined["action_date"], errors="coerce")
    combined = combined.sort_values("action_date")
    combined["action_date"] = combined["action_date"].dt.strftime("%Y-%m-%d")

    combined.to_csv(DOI_OUTPUT_CSV, index=False)
    print(f"\nWrote {len(combined):,} transactions → {DOI_OUTPUT_CSV}")
    print(f"Unique awards: {combined['contract_award_unique_key'].nunique():,}")
    print(f"Date range: {combined['action_date'].min()} to {combined['action_date'].max()}")

    nps = derive_nps_subset(combined)
    if len(nps) == 0:
        print("WARNING: NPS subset is empty — check awarding_sub_agency_name values in DOI data")
    nps.to_csv(NPS_OUTPUT_CSV, index=False)
    print(f"Derived NPS subset: {len(nps):,} transactions → {NPS_OUTPUT_CSV}")
    print(f"NPS unique awards: {nps['contract_award_unique_key'].nunique():,}")

    print("\n--- Running compare_admins ---")
    import compare_admins
    compare_admins.main()

    print("\n--- Building doi_viz.html ---")
    import build_doi_viz
    build_doi_viz.main()

    print("\n--- Building viz.html ---")
    import build_viz
    build_viz.main()


if __name__ == "__main__":
    main()
