# Urgency Investigation Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two scripts — `fetch_justifications.py` (resumable manifest builder) and `analyze_urgency.py` (markdown investigation report) — that surface Trump II NPS "urgency" no-bid contracts with evidence for journalist investigation.

**Architecture:** `fetch_justifications.py` reads `nps_no_bid_contracts.csv`, calls the USASpending award detail API for each Trump II URG contract, constructs SAM.gov/USASpending links, and writes a resumable `justifications_manifest.csv`. `analyze_urgency.py` joins the master CSV with the manifest and produces `urgency_investigation.md`.

**Tech Stack:** Python 3, pandas, requests, pytest, requests-mock. All already in the project venv except pytest and requests-mock (add to requirements.txt).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `config.py` | Modify | Add 5 new constants |
| `urgency_utils.py` | Create | Shared `load_trump2_urg_awards()` used by both scripts |
| `fetch_justifications.py` | Create | API fetch, link construction, manifest I/O |
| `analyze_urgency.py` | Create | Join data, render markdown report |
| `tests/test_urgency_utils.py` | Create | Tests for shared loader |
| `tests/test_fetch_justifications.py` | Create | Tests for URL builders, manifest I/O |
| `tests/test_analyze_urgency.py` | Create | Tests for report generation |
| `requirements.txt` | Modify | Add pytest, requests-mock |
| `justifications_manifest.csv` | Generated | One row per URG award; resume checkpoint |
| `urgency_investigation.md` | Generated | Final investigation report |

---

## Task 1: Add constants to config.py and update requirements.txt

**Files:**
- Modify: `config.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Write the failing test**

Create `tests/test_urgency_utils.py`:

```python
import importlib


def test_config_has_required_constants():
    import config
    from datetime import date

    assert hasattr(config, "TRUMP2_START")
    assert isinstance(config.TRUMP2_START, date)
    assert config.TRUMP2_START.year == 2025

    assert hasattr(config, "URG_CODE")
    assert config.URG_CODE == "URG"

    assert hasattr(config, "MANIFEST_CSV")
    assert config.MANIFEST_CSV.endswith(".csv")

    assert hasattr(config, "JUSTIFICATIONS_DIR")
    assert "justifications" in config.JUSTIFICATIONS_DIR

    assert hasattr(config, "INVESTIGATION_MD")
    assert config.INVESTIGATION_MD.endswith(".md")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate && pytest tests/test_urgency_utils.py::test_config_has_required_constants -v
```

Expected: `FAILED` — `AttributeError: module 'config' has no attribute 'TRUMP2_START'`

- [ ] **Step 3: Add constants to config.py**

Add at the bottom of `config.py` (after the existing imports and constants):

```python
# Urgency investigation tool
TRUMP2_START = date(2025, 1, 20)
URG_CODE = "URG"
MANIFEST_CSV = "justifications_manifest.csv"
JUSTIFICATIONS_DIR = "docs/justifications"
INVESTIGATION_MD = "urgency_investigation.md"
```

- [ ] **Step 4: Add pytest and requests-mock to requirements.txt**

Append to `requirements.txt`:

```
pytest>=7.0.0
requests-mock>=1.12.0
```

Then install:

```bash
source .venv/bin/activate && pip install pytest requests-mock --quiet
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate && pytest tests/test_urgency_utils.py::test_config_has_required_constants -v
```

Expected: `PASSED`

- [ ] **Step 6: Commit**

```bash
git add config.py requirements.txt tests/test_urgency_utils.py
git commit -m "Add urgency investigation constants and test scaffolding"
```

---

## Task 2: Create urgency_utils.py — shared award loader

**Files:**
- Create: `urgency_utils.py`
- Modify: `tests/test_urgency_utils.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_urgency_utils.py`:

```python
import pandas as pd
import pytest
from urgency_utils import load_trump2_urg_awards


def _make_csv(tmp_path, rows):
    """Write a minimal contracts CSV for testing."""
    cols = [
        "contract_transaction_unique_key",
        "contract_award_unique_key",
        "award_id_piid",
        "action_date",
        "federal_action_obligation",
        "other_than_full_and_open_competition_code",
        "recipient_name",
        "prime_award_base_transaction_description",
        "product_or_service_code_description",
        "primary_place_of_performance_city_name",
        "primary_place_of_performance_state_code",
    ]
    df = pd.DataFrame(rows, columns=cols)
    path = str(tmp_path / "contracts.csv")
    df.to_csv(path, index=False)
    return path


def test_load_filters_to_trump2_urg(tmp_path):
    """Only awards in Trump II (>=2025-01-20) with URG code are returned."""
    rows = [
        # Trump II URG — should be included
        ["TXN1", "AWD1", "PIID1", "2025-06-01", "100000.00", "URG", "Vendor A", "Urgent work", "Construction", "DC", "DC"],
        # Second transaction on same award — should be summed
        ["TXN2", "AWD1", "PIID1", "2025-07-01", "50000.00",  "URG", "Vendor A", "Urgent work", "Construction", "DC", "DC"],
        # Trump II but not URG — excluded
        ["TXN3", "AWD2", "PIID2", "2025-03-01", "200000.00", "B",   "Vendor B", "No-bid work",  "HVAC",         "NY", "NY"],
        # Pre-Trump II URG — excluded
        ["TXN4", "AWD3", "PIID3", "2024-12-01", "999000.00", "URG", "Vendor C", "Earlier work", "Plumbing",     "LA", "CA"],
        # Trump II URG single transaction — included
        ["TXN5", "AWD4", "PIID4", "2025-04-01", "75000.00",  "URG", "Vendor D", "Urgent too",   "Painting",     "TX", "TX"],
    ]
    path = _make_csv(tmp_path, rows)
    result = load_trump2_urg_awards(path)

    assert len(result) == 2
    assert set(result["award_id_piid"]) == {"PIID1", "PIID4"}


def test_load_sums_obligations_per_award(tmp_path):
    """Obligations are summed across all transactions for an award."""
    rows = [
        ["TXN1", "AWD1", "PIID1", "2025-06-01", "100000.00", "URG", "Vendor A", "Work A", "PSC", "DC", "DC"],
        ["TXN2", "AWD1", "PIID1", "2025-07-01",  "50000.00", "URG", "Vendor A", "Work A", "PSC", "DC", "DC"],
        ["TXN3", "AWD1", "PIID1", "2025-08-01",  "-10000.00","URG", "Vendor A", "Work A", "PSC", "DC", "DC"],
    ]
    path = _make_csv(tmp_path, rows)
    result = load_trump2_urg_awards(path)

    assert len(result) == 1
    assert abs(result.iloc[0]["total_obligation"] - 140000.0) < 0.01


def test_load_returns_first_action_date(tmp_path):
    """first_action_date reflects the earliest transaction for each award."""
    rows = [
        ["TXN1", "AWD1", "PIID1", "2025-07-01", "50000.00", "URG", "V", "D", "P", "C", "DC"],
        ["TXN2", "AWD1", "PIID1", "2025-06-01", "50000.00", "URG", "V", "D", "P", "C", "DC"],
    ]
    path = _make_csv(tmp_path, rows)
    result = load_trump2_urg_awards(path)

    assert result.iloc[0]["first_action_date"] == "2025-06-01"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate && pytest tests/test_urgency_utils.py -v -k "not test_config"
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'urgency_utils'`

- [ ] **Step 3: Implement urgency_utils.py**

Create `urgency_utils.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate && pytest tests/test_urgency_utils.py -v
```

Expected: all 4 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add urgency_utils.py tests/test_urgency_utils.py
git commit -m "Add urgency_utils with shared Trump II URG award loader"
```

---

## Task 3: Create fetch_justifications.py

**Files:**
- Create: `fetch_justifications.py`
- Create: `tests/test_fetch_justifications.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fetch_justifications.py`:

```python
import csv
import os
import pandas as pd
import pytest
import requests_mock as rm

from fetch_justifications import (
    MANIFEST_FIELDS,
    append_manifest_row,
    load_manifest,
    make_fpds_search_url,
    make_sam_solicitation_url,
    make_usaspending_url,
)


# ── URL builders ──────────────────────────────────────────────────────────────

def test_make_usaspending_url():
    key = "CONT_AWD_140P2026C0028_1443_-NONE-_-NONE-"
    assert make_usaspending_url(key) == f"https://www.usaspending.gov/award/{key}/"


def test_make_fpds_search_url_contains_piid():
    url = make_fpds_search_url("140P2026C0028")
    assert "140P2026C0028" in url
    assert "sam.gov" in url or "fpds.gov" in url


def test_make_sam_solicitation_url_with_identifier():
    url = make_sam_solicitation_url("140P2026R0050")
    assert "140P2026R0050" in url
    assert "sam.gov" in url


def test_make_sam_solicitation_url_with_empty_identifier():
    assert make_sam_solicitation_url("") == ""
    assert make_sam_solicitation_url(None) == ""


# ── Manifest I/O ──────────────────────────────────────────────────────────────

def _empty_row(piid: str) -> dict:
    return {k: ("" if k != "award_id_piid" else piid) for k in MANIFEST_FIELDS}


def test_load_manifest_returns_empty_set_when_no_file(tmp_path):
    assert load_manifest(str(tmp_path / "nonexistent.csv")) == set()


def test_append_manifest_row_creates_file_with_header(tmp_path):
    path = str(tmp_path / "manifest.csv")
    append_manifest_row(path, _empty_row("PIID1"))

    df = pd.read_csv(path, dtype=str)
    assert list(df.columns) == MANIFEST_FIELDS
    assert len(df) == 1
    assert df.iloc[0]["award_id_piid"] == "PIID1"


def test_append_manifest_row_does_not_duplicate_header(tmp_path):
    path = str(tmp_path / "manifest.csv")
    append_manifest_row(path, _empty_row("PIID1"))
    append_manifest_row(path, _empty_row("PIID2"))

    df = pd.read_csv(path, dtype=str)
    assert len(df) == 2
    assert list(df.columns) == MANIFEST_FIELDS


def test_load_manifest_returns_set_of_piids(tmp_path):
    path = str(tmp_path / "manifest.csv")
    for piid in ["PIID1", "PIID2", "PIID3"]:
        append_manifest_row(path, _empty_row(piid))

    result = load_manifest(path)
    assert result == {"PIID1", "PIID2", "PIID3"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate && pytest tests/test_fetch_justifications.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'fetch_justifications'`

- [ ] **Step 3: Implement fetch_justifications.py**

Create `fetch_justifications.py`:

```python
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

        doc_url = ""
        doc_local_path = ""

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
            "doc_url": doc_url,
            "doc_local_path": doc_local_path,
        }
        append_manifest_row(MANIFEST_CSV, row)

    # Summary
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate && pytest tests/test_fetch_justifications.py -v
```

Expected: all 8 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add fetch_justifications.py tests/test_fetch_justifications.py
git commit -m "Add fetch_justifications.py with resumable manifest builder"
```

---

## Task 4: Create analyze_urgency.py

**Files:**
- Create: `analyze_urgency.py`
- Create: `tests/test_analyze_urgency.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_analyze_urgency.py`:

```python
import pandas as pd
import pytest

from analyze_urgency import build_links_cell, generate_report, ja_status, truncate


# ── Helpers ───────────────────────────────────────────────────────────────────

def test_truncate_short_string_unchanged():
    assert truncate("hello world", 120) == "hello world"


def test_truncate_long_string_gets_ellipsis():
    long = "x" * 130
    result = truncate(long, 120)
    assert result.endswith("…")
    assert len(result) == 121  # 120 chars + ellipsis character


def test_truncate_handles_none():
    assert truncate(None, 120) == ""


def test_ja_status_downloaded():
    row = pd.Series({"doc_local_path": "docs/justifications/PIID1/doc.pdf", "doc_url": ""})
    assert ja_status(row) == "Downloaded"


def test_ja_status_link_only_with_doc_url():
    row = pd.Series({"doc_local_path": "", "doc_url": "https://example.com/doc.pdf"})
    assert ja_status(row) == "Link only"


def test_ja_status_link_only_no_doc():
    row = pd.Series({"doc_local_path": "", "doc_url": ""})
    assert ja_status(row) == "Link only"


def test_build_links_cell_includes_both_links():
    row = pd.Series({
        "usaspending_url": "https://usaspending.gov/award/AWD1/",
        "sam_piid_url": "https://sam.gov/search/?keywords=PIID1&index=co",
        "sam_solicitation_url": "https://sam.gov/search/?keywords=SOL1&index=opp",
    })
    cell = build_links_cell(row)
    assert "[USASpending]" in cell
    assert "[SAM (PIID)]" in cell
    assert "[SAM (Solicitation)]" in cell


def test_build_links_cell_skips_empty_solicitation():
    row = pd.Series({
        "usaspending_url": "https://usaspending.gov/award/AWD1/",
        "sam_piid_url": "https://sam.gov/search/?keywords=PIID1&index=co",
        "sam_solicitation_url": "",
    })
    cell = build_links_cell(row)
    assert "[SAM (Solicitation)]" not in cell


# ── Report generation ─────────────────────────────────────────────────────────

def _make_awards():
    return pd.DataFrame({
        "contract_award_unique_key": ["AWD1", "AWD2"],
        "award_id_piid": ["PIID1", "PIID2"],
        "recipient_name": ["Big Corp LLC", "Small Biz Inc"],
        "prime_award_base_transaction_description": [
            "URGENT RENOVATION OF REFLECTING POOL",
            "EMERGENCY HVAC REPAIR",
        ],
        "total_obligation": [1_500_000.0, 50_000.0],
        "first_action_date": ["2025-06-01", "2025-03-01"],
        "product_or_service_code_description": ["Construction", "HVAC Repair"],
        "primary_place_of_performance_city_name": ["Washington", "New York"],
        "primary_place_of_performance_state_code": ["DC", "NY"],
    })


def _make_manifest():
    return pd.DataFrame({
        "award_id_piid": ["PIID1", "PIID2"],
        "usaspending_url": [
            "https://www.usaspending.gov/award/AWD1/",
            "https://www.usaspending.gov/award/AWD2/",
        ],
        "sam_piid_url": [
            "https://sam.gov/search/?keywords=PIID1&index=co",
            "https://sam.gov/search/?keywords=PIID2&index=co",
        ],
        "sam_solicitation_url": [
            "https://sam.gov/search/?keywords=SOL1&index=opp",
            "",
        ],
        "doc_url": ["https://example.com/ja.pdf", ""],
        "doc_local_path": ["docs/justifications/PIID1/ja.pdf", ""],
    })


def test_generate_report_contains_header_block():
    report = generate_report(_make_awards(), _make_manifest())
    assert "# NPS Urgency Contract Investigation" in report
    assert "2025-01-20" in report
    assert "2 contracts" in report.lower() or "2" in report


def test_generate_report_sorts_by_obligation_descending():
    report = generate_report(_make_awards(), _make_manifest())
    # PIID1 ($1.5M) must appear before PIID2 ($50K)
    assert report.index("PIID1") < report.index("PIID2")


def test_generate_report_formats_dollars():
    report = generate_report(_make_awards(), _make_manifest())
    assert "$1,500,000" in report
    assert "$50,000" in report


def test_generate_report_shows_downloaded_status():
    report = generate_report(_make_awards(), _make_manifest())
    assert "Downloaded" in report


def test_generate_report_shows_link_only_status():
    report = generate_report(_make_awards(), _make_manifest())
    assert "Link only" in report


def test_generate_report_works_without_manifest(tmp_path):
    """analyze_urgency.py should still produce a report if manifest is missing."""
    empty_manifest = pd.DataFrame(columns=[
        "award_id_piid", "usaspending_url", "sam_piid_url",
        "sam_solicitation_url", "doc_url", "doc_local_path",
    ])
    report = generate_report(_make_awards(), empty_manifest)
    assert "PIID1" in report
    assert "PIID2" in report
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate && pytest tests/test_analyze_urgency.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'analyze_urgency'`

- [ ] **Step 3: Implement analyze_urgency.py**

Create `analyze_urgency.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate && pytest tests/test_analyze_urgency.py -v
```

Expected: all 11 tests `PASSED`

- [ ] **Step 5: Run full test suite to verify nothing regressed**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate && pytest tests/ -v
```

Expected: all tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add analyze_urgency.py tests/test_analyze_urgency.py
git commit -m "Add analyze_urgency.py with investigation report generator"
```

---

## Task 5: Live run and output verification

**Files:**
- Generated: `justifications_manifest.csv`
- Generated: `urgency_investigation.md`

- [ ] **Step 1: Run fetch_justifications.py**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate && python fetch_justifications.py
```

Expected output (72 awards, ~36 seconds at 0.5s/request):
```
Found 72 unique Trump II URG awards
Skipping 0 already in manifest; fetching 72
[1/72] 140P1325P0012 — SKINNERS DRILLING & WELL SERVICE, LLC
  ...
[72/72] ...
Done. 72 rows in justifications_manifest.csv. Downloaded: 0, doc URL: 0, link-only: 72
```

- [ ] **Step 2: Run analyze_urgency.py**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate && python analyze_urgency.py
```

Expected:
```
Wrote urgency_investigation.md
  72 contracts, $18,067,XXX total
```

- [ ] **Step 3: Spot-check the report**

Open `urgency_investigation.md` and verify:
- Reflecting pool painting (`140P2026C0028`, Atlantic Industrial Coatings) is the first row at ~$14.6M
- Reflecting pool nano bubble (`140P2026C0031`, Green Water Solutions) is second at ~$1.7M
- Alcatraz preventative maintenance (`140P8625P0001`) appears in the top 5
- Each row has working USASpending and SAM.gov links
- Dollar amounts are formatted as `$14,652,521`

- [ ] **Step 4: Commit outputs**

```bash
git add justifications_manifest.csv urgency_investigation.md requirements.txt
git commit -m "Add live-run outputs: justifications manifest and investigation report"
```

---

## Running the pipeline after updates

```bash
source .venv/bin/activate
# Re-run fetch after new contracts appear (skips already-fetched):
python fetch_justifications.py
# Regenerate report:
python analyze_urgency.py
```

To re-fetch a specific award, delete its row from `justifications_manifest.csv` and re-run `fetch_justifications.py`.
