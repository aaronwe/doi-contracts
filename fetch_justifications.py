#!/usr/bin/env python3
"""
Fetch Justification & Approval documents for Trump II NPS urgency-coded contracts.

Produces:
  justifications_manifest.csv  — one row per unique award (resumable)
  docs/justifications/{piid}/  — downloaded files when available (best-effort)

Usage:
    source .venv/bin/activate
    python fetch_justifications.py
"""

import csv
import os
import time

import pandas as pd
import requests

from config import API_BASE, JUSTIFICATIONS_DIR, MANIFEST_CSV
from urgency_utils import load_trump2_urg_awards

REQUEST_DELAY = 0.5  # seconds between API calls

MANIFEST_FIELDS = [
    "award_id_piid",
    "contract_award_unique_key",
    "recipient_name",
    "description",
    "total_obligation",
    "first_action_date",
    "psc_description",
    "state",
    "usaspending_url",
    "sam_piid_url",
    "sam_solicitation_url",
    "doc_url",
    "doc_local_path",
]


# ── URL builders ──────────────────────────────────────────────────────────────

def make_usaspending_url(award_key: str) -> str:
    return f"https://www.usaspending.gov/award/{award_key}/"


def make_fpds_search_url(piid: str) -> str:
    return f"https://sam.gov/search/?keywords={piid}&index=co"


def make_sam_solicitation_url(solicitation_id: str) -> str:
    if not solicitation_id:
        return ""
    return f"https://sam.gov/search/?keywords={solicitation_id}&index=opp"


# ── Manifest I/O ──────────────────────────────────────────────────────────────

def load_manifest(manifest_csv: str) -> set:
    """Return set of award_id_piid values already processed."""
    if not os.path.exists(manifest_csv):
        return set()
    df = pd.read_csv(manifest_csv, dtype=str)
    return set(df["award_id_piid"].dropna().tolist())


def append_manifest_row(manifest_csv: str, row: dict) -> None:
    """Append one row to the manifest CSV, writing header only when creating a new file."""
    write_header = not os.path.exists(manifest_csv)
    with open(manifest_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in MANIFEST_FIELDS})


# ── API calls ─────────────────────────────────────────────────────────────────

def fetch_award_detail(award_key: str) -> dict:
    """Call USASpending award detail API. Returns parsed JSON or empty dict on error."""
    url = f"{API_BASE}/awards/{award_key}/"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as exc:
        print(f"  USASpending API error: {exc}")
        return {}


def download_doc(url: str, dest_dir: str) -> str:
    """Download a file to dest_dir. Returns local path or empty string on failure."""
    os.makedirs(dest_dir, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0] or "document.pdf"
    local_path = os.path.join(dest_dir, filename)
    try:
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        return local_path
    except requests.exceptions.RequestException as exc:
        print(f"  download failed: {exc}")
        return ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    os.makedirs(JUSTIFICATIONS_DIR, exist_ok=True)

    awards = load_trump2_urg_awards()
    print(f"Found {len(awards)} unique Trump II URG awards")

    already_done = load_manifest(MANIFEST_CSV)
    remaining = awards[~awards["award_id_piid"].isin(already_done)].copy()
    print(f"Skipping {len(already_done)} already in manifest; fetching {len(remaining)}")

    for i, (_, award) in enumerate(remaining.iterrows(), 1):
        piid = award["award_id_piid"]
        key = award["contract_award_unique_key"]
        print(f"[{i}/{len(remaining)}] {piid} — {str(award['recipient_name'])[:50]}")

        detail = fetch_award_detail(key)
        time.sleep(REQUEST_DELAY)

        solicitation_id = ""
        if detail:
            ltd = detail.get("latest_transaction_contract_data") or {}
            solicitation_id = ltd.get("solicitation_identifier") or ""

        row = {
            "award_id_piid": piid,
            "contract_award_unique_key": key,
            "recipient_name": award["recipient_name"],
            "description": award["prime_award_base_transaction_description"],
            "total_obligation": f"{award['total_obligation']:.2f}",
            "first_action_date": award["first_action_date"],
            "psc_description": award.get("product_or_service_code_description", ""),
            "state": award.get("primary_place_of_performance_state_code", ""),
            "usaspending_url": make_usaspending_url(key),
            "sam_piid_url": make_fpds_search_url(piid),
            "sam_solicitation_url": make_sam_solicitation_url(solicitation_id),
            "doc_url": "",
            "doc_local_path": "",
        }
        append_manifest_row(MANIFEST_CSV, row)

    if os.path.exists(MANIFEST_CSV):
        manifest_df = pd.read_csv(MANIFEST_CSV, dtype=str)
        n_downloaded = (manifest_df["doc_local_path"].fillna("") != "").sum()
        n_doc_url = (manifest_df["doc_url"].fillna("") != "").sum()
        print(
            f"\nDone. {len(manifest_df)} rows in {MANIFEST_CSV}. "
            f"Downloaded: {n_downloaded}, doc URL: {n_doc_url}, link-only: {len(manifest_df) - n_downloaded - n_doc_url}"
        )


if __name__ == "__main__":
    main()
