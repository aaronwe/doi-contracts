# Urgency-Only Viz Refocus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refocus NPS and DOI visualizations to show only urgency-justified (FAR 6.302-2) no-bid contracts, adding a dual-filter contract table to the DOI viz.

**Architecture:** `viz.html` is a manual static update (no build script). The DOI viz is regenerated from `doi_no_bid_contracts.csv` via `build_doi_viz.py`, which now applies an urgency filter and emits a flat `contracts` array; `doi_viz_template.html` gains an admin dropdown, a simplified single-category chart, and a responsive contract table. Both chart and table respond to the agency and admin filters; selecting a specific admin hides the other admin bars entirely.

**Tech Stack:** Python/pandas (`build_doi_viz.py`), vanilla JS + Chart.js 4.4.1 (`doi_viz_template.html`), pytest.

**Spec:** `docs/superpowers/specs/2026-06-23-urgency-only-viz-design.md`

---

## File Map

| File | Change |
|---|---|
| `viz.html` | Manual update — urgency-only numbers, single-dataset chart |
| `tests/test_build_doi_viz.py` | Remove defunct tests; add `build_contracts_table` tests |
| `build_doi_viz.py` | Urgency filter; remove breakdown functions; add `build_contracts_table` |
| `doi_viz_template.html` | Admin dropdown, simplified chart logic, contract table |
| `doi_viz.html` | Regenerated artifact — `python build_doi_viz.py` |

---

## Task 1: Update `viz.html` — NPS urgency-only

**Files:**
- Modify: `viz.html`

Urgency-only numbers (first 520 days): Trump I $1.353M/55 contracts, Biden $2.518M/66, Trump II $21.191M/73.

- [ ] **Step 1: Update the subtitle**

Replace (line ~156):
```html
      First 519 days in office · Urgency, follow-on, and other discretionary no-bid contracts ·
      Excludes statutory (AbilityOne/8(a)), utilities, and sole-source IDV task orders
```
With:
```html
      Urgency (FAR 6.302-2) no-bid contracts · First 520 days ·
      Excludes statutory (AbilityOne/8(a)), utilities, and sole-source IDV task orders
```

- [ ] **Step 2: Update the stat cards**

Replace the three `.card` divs (lines ~161–177):
```html
    <div class="cards">
      <div class="card">
        <div class="card-label">Trump I</div>
        <div class="card-value">$1.4M</div>
        <div class="card-sub">55 new contracts</div>
      </div>
      <div class="card">
        <div class="card-label">Biden</div>
        <div class="card-value">$2.5M</div>
        <div class="card-sub">66 new contracts</div>
      </div>
      <div class="card highlight">
        <div class="card-label">Trump II</div>
        <div class="card-value">$21.2M</div>
        <div class="card-sub">73 new contracts</div>
      </div>
    </div>
```

- [ ] **Step 3: Update the legend — remove Follow-on and Other entries**

Replace the `.legend` div (lines ~178–182):
```html
    <div class="legend">
      <span class="legend-item"><span class="legend-swatch" style="background:#E24B4A;"></span>Urgency (FAR 6.302-2)</span>
    </div>
```

- [ ] **Step 4: Update the chart aria-label and fallback text**

Replace the `<canvas>` inner content (lines ~185–190):
```html
      <canvas id="chart" role="img"
        aria-label="Bar chart of NPS urgency no-bid contracts, first 520 days. Trump I: $1.4M (55 contracts). Biden: $2.5M (66 contracts). Trump II: $21.2M (73 contracts).">
        Trump I: $1.4M — 55 urgency contracts.
        Biden: $2.5M — 66 urgency contracts.
        Trump II: $21.2M — 73 urgency contracts.
      </canvas>
```

- [ ] **Step 5: Replace the Chart.js datasets block**

Replace the entire `datasets:` array inside the `new Chart(...)` call (lines ~219–236):
```javascript
        datasets: [
          {
            label: 'Urgency (FAR 6.302-2)',
            data: [1.353, 2.518, 21.191],
            backgroundColor: '#E24B4A',
          },
        ]
```

- [ ] **Step 6: Update the callout**

Replace the `.callout` div (lines ~193–198):
```html
    <div class="callout">
      NPS urgency contracts (FAR 6.302-2) total <strong>$21.2M under Trump II</strong> —
      8× Biden's $2.5M and nearly 16× Trump I's $1.4M, within the same first 520-day window.
    </div>
```

- [ ] **Step 7: Update the source note**

Replace the `.source` paragraph (lines ~200–210):
```html
    <p class="source">
      First 520 days per administration (Jan. 20 inauguration through equivalent date).
      Counts contracts by first award date (excludes modifications from prior administrations).
      Includes urgency task orders under IDV/GSA Schedule vehicles. Excludes AbilityOne/8(a) (OTH),
      regulated utilities (UT), only-one-source (ONE), and unique-source (UNQ).
      Source: <a href="https://api.usaspending.gov">USASpending.gov</a> FPDS bulk download,
      transaction-level data.
      Analysis: <a href="https://github.com/aaronwe/doi-contracts">github.com/aaronwe/doi-contracts</a>.
    </p>
```

- [ ] **Step 8: Verify the HTML renders correctly**

Open `viz.html` in a browser. Confirm:
- Three solid red bars (no stacking), Trump II bar is ~8× taller than Biden
- Cards show $1.4M/55, $2.5M/66, $21.2M/73
- Legend shows only "Urgency (FAR 6.302-2)"
- Tooltip on each bar shows the urgency value and a "Total:" footer

- [ ] **Step 9: Commit**

```bash
git add viz.html
git commit -m "Update viz.html to urgency-only: single-dataset chart, updated numbers and callout"
```

---

## Task 2: Update tests — remove defunct tests, add `build_contracts_table` tests

**Files:**
- Modify: `tests/test_build_doi_viz.py`

The existing test file tests `classify_justification` and `aggregate_agency_breakdown`, which are being deleted. Those tests must be removed and new tests for `build_contracts_table` added.

- [ ] **Step 1: Replace the imports block at the top of the test file**

Replace lines 1–17:
```python
import json
import pandas as pd
import pytest
from datetime import date, timedelta

from build_doi_viz import (
    INJECTION_MARKER,
    inject_and_write,
    aggregate_doi_obligations,
    build_contracts_table,
    compute_window,
    VIZ_ADMIN_NAMES,
)
```

- [ ] **Step 2: Remove the `classify_justification` test block**

Delete lines 20–49 (all seven `test_classify_*` functions and the section comment).

- [ ] **Step 3: Remove the `aggregate_agency_breakdown` test block**

Delete the two `test_breakdown_*` functions and the section comment (currently near the bottom of the file).

- [ ] **Step 4: Add `_make_full_df` fixture helper**

Add this helper immediately after the existing `_windows_for` helper:
```python
def _make_full_df(rows):
    """rows: list of (date_str, award_key, piid, agency, obligation, state, vendor, description)"""
    return pd.DataFrame([
        {
            "action_date":                              pd.Timestamp(r[0]),
            "contract_award_unique_key":                r[1],
            "award_id_piid":                            r[2],
            "awarding_sub_agency_name":                 r[3],
            "federal_action_obligation":                float(r[4]),
            "primary_place_of_performance_state_code":  r[5],
            "recipient_name":                           r[6],
            "transaction_description":                  r[7],
            "prime_award_base_transaction_description": r[7],
        }
        for r in rows
    ])
```

- [ ] **Step 5: Add `build_contracts_table` tests**

Add this block at the end of the file:
```python
# ── build_contracts_table ────────────────────────────────────────────────────

def test_contracts_table_sorted_by_amount_desc():
    df = _make_full_df([
        ("2025-02-01", "AWD-1", "P001", "National Park Service", 500_000,   "DC", "Vendor A", "Work A"),
        ("2025-03-01", "AWD-2", "P002", "National Park Service", 2_000_000, "DC", "Vendor B", "Work B"),
        ("2025-04-01", "AWD-3", "P003", "National Park Service", 100_000,   "DC", "Vendor C", "Work C"),
    ])
    windows = _windows_for(["Trump II"])
    result = build_contracts_table(df, ["Trump II"], windows)
    amounts = [r["amount"] for r in result]
    assert amounts == sorted(amounts, reverse=True)


def test_contracts_table_row_has_required_keys():
    df = _make_full_df([
        ("2025-02-01", "AWD-1", "P001", "National Park Service", 1_000_000, "DC", "Vendor A", "Work"),
    ])
    windows = _windows_for(["Trump II"])
    result = build_contracts_table(df, ["Trump II"], windows)
    assert len(result) == 1
    for key in ("piid", "vendor", "description", "agency", "agency_short", "state",
                "date", "amount", "url", "admin"):
        assert key in result[0], f"missing key: {key}"


def test_contracts_table_assigns_admin_label():
    df = _make_full_df([
        ("2017-02-01", "AWD-1", "P001", "National Park Service", 1_000_000, "DC", "Vendor A", "T1 work"),
        ("2025-02-01", "AWD-2", "P002", "National Park Service", 2_000_000, "DC", "Vendor B", "T2 work"),
    ])
    windows = _windows_for(["Trump I", "Trump II"])
    result = build_contracts_table(df, ["Trump I", "Trump II"], windows)
    by_piid = {r["piid"]: r["admin"] for r in result}
    assert by_piid["P001"] == "Trump I"
    assert by_piid["P002"] == "Trump II"


def test_contracts_table_sums_multi_transaction_award():
    df = _make_full_df([
        ("2025-02-01", "AWD-1", "P001", "National Park Service", 1_000_000, "DC", "V", "D"),
        ("2025-03-01", "AWD-1", "P001", "National Park Service",   500_000, "DC", "V", "D"),
        ("2025-04-01", "AWD-1", "P001", "National Park Service",  -100_000, "DC", "V", "D"),
    ])
    windows = _windows_for(["Trump II"])
    result = build_contracts_table(df, ["Trump II"], windows)
    assert len(result) == 1
    assert abs(result[0]["amount"] - 1.4) < 0.001


def test_contracts_table_excludes_pre_window_originating_award():
    df = _make_full_df([
        # Originated before Trump II, modified during — must be excluded
        ("2024-12-15", "AWD-OLD", "P001", "National Park Service", 1_000_000, "DC", "V", "D"),
        ("2025-02-01", "AWD-OLD", "P001", "National Park Service",   500_000, "DC", "V", "D"),
        # Originated in Trump II — must be included
        ("2025-02-01", "AWD-NEW", "P002", "National Park Service", 2_000_000, "DC", "V", "D"),
    ])
    windows = _windows_for(["Trump II"])
    result = build_contracts_table(df, ["Trump II"], windows)
    assert len(result) == 1
    assert result[0]["piid"] == "P002"


def test_contracts_table_uses_agency_short_name():
    df = _make_full_df([
        ("2025-02-01", "AWD-1", "P001", "National Park Service", 1_000_000, "DC", "V", "D"),
    ])
    windows = _windows_for(["Trump II"])
    result = build_contracts_table(df, ["Trump II"], windows)
    assert result[0]["agency_short"] == "NPS"
    assert result[0]["agency"] == "National Park Service"


def test_contracts_table_usaspending_url_contains_award_key():
    df = _make_full_df([
        ("2025-02-01", "CONT_AWD_140P2026C0028_1443_-NONE-_-NONE-", "P001",
         "National Park Service", 1_000_000, "DC", "V", "D"),
    ])
    windows = _windows_for(["Trump II"])
    result = build_contracts_table(df, ["Trump II"], windows)
    assert "CONT_AWD_140P2026C0028_1443_-NONE-_-NONE-" in result[0]["url"]
    assert result[0]["url"].startswith("https://www.usaspending.gov/award/")
```

- [ ] **Step 6: Run the tests to confirm they fail correctly**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate
pytest tests/test_build_doi_viz.py -v 2>&1 | tail -30
```

Expected: import error or `build_contracts_table` not found. The `inject_and_write` and `aggregate_doi_obligations` tests may still pass — that's fine. The new `test_contracts_table_*` tests must be failing (not passing by coincidence).

---

## Task 3: Rewrite `build_doi_viz.py` — urgency filter + contracts table

**Files:**
- Modify: `build_doi_viz.py`

- [ ] **Step 1: Update the imports block**

Replace lines 1–24:
```python
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
```

- [ ] **Step 2: Replace the constants block**

Replace everything from `TRUMP_II_INAUGURATION = ...` down through `INJECTION_MARKER = ...` with:
```python
TRUMP_II_INAUGURATION = TRUMP2_START
EXCLUDE_JUSTIFICATION_CODES = {"OTH", "UT", "ONE", "UNQ"}
EXCLUDE_AGENCIES = {"Departmental Offices"}
OTHER_THRESHOLD_DOLLARS = 100_000

AGENCY_COLORS = {
    "National Park Service":                                "#E24B4A",
    "Bureau of Land Management":                            "#EF9F27",
    "Bureau of Indian Affairs and Bureau of Indian Education": "#4A90D9",
    "U.S. Fish and Wildlife Service":                       "#5BAD6F",
    "U.S. Geological Survey":                               "#9B59B6",
    "Bureau of Reclamation":                                "#1A7CBF",
    "Departmental Offices":                                 "#C45E00",
    "Other DOI bureaus":                                    "#888780",
}
FALLBACK_COLORS = ["#2E7D32", "#6A1B9A", "#00695C", "#4E342E", "#37474F"]

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
```

- [ ] **Step 3: Replace `load_contracts()` — add urgency filter**

Replace the entire `load_contracts` function:
```python
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
```

- [ ] **Step 4: Remove `classify_justification()` and `aggregate_agency_breakdown()`**

Delete the entire bodies of both functions (they are no longer used). Keep `compute_window()` and `aggregate_doi_obligations()` — those are unchanged.

- [ ] **Step 5: Add `build_contracts_table()` after `aggregate_doi_obligations`**

```python
def build_contracts_table(
    df: pd.DataFrame, admin_names: list, windows: dict
) -> list:
    contracts = []
    for admin_name in admin_names:
        start, end = windows[admin_name]
        window_mask = (df["action_date"] >= start) & (df["action_date"] <= end)
        window_df   = df[window_mask]

        first_dates = window_df.groupby("contract_award_unique_key")["action_date"].min()
        originated  = first_dates[first_dates >= start].index
        award_df    = window_df[window_df["contract_award_unique_key"].isin(originated)]

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
                str(row.get("transaction_description") or "")
                or str(row.get("prime_award_base_transaction_description") or "")
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
```

- [ ] **Step 6: Replace `build_data()` — remove agency_breakdown, add contracts**

```python
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
```

- [ ] **Step 7: Update `main()` — remove agency_breakdown reference**

```python
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
```

- [ ] **Step 8: Run the full test suite**

```bash
pytest tests/test_build_doi_viz.py -v
```

Expected: all tests pass, including the new `test_contracts_table_*` tests. The `test_classify_*` and `test_breakdown_*` tests should be gone.

- [ ] **Step 9: Commit**

```bash
git add build_doi_viz.py tests/test_build_doi_viz.py
git commit -m "Refocus build_doi_viz.py to urgency-only; add build_contracts_table"
```

---

## Task 4: Rewrite `doi_viz_template.html` — admin dropdown, simplified chart, contract table

**Files:**
- Modify: `doi_viz_template.html`

This replaces the entire file. Write the complete new template:

- [ ] **Step 1: Write the new `doi_viz_template.html`**

```html
<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DOI Urgency No-Bid Contracts by Administration</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 16px; line-height: 1.6; color: #1a1a1a; background: #fff;
      padding: 2.5rem 1.5rem;
    }
    .container { max-width: 780px; margin: 0 auto; }
    .eyebrow {
      font-size: 12px; font-weight: 500; letter-spacing: .08em;
      text-transform: uppercase; color: #888; margin-bottom: .5rem;
    }
    h1 { font-size: 22px; font-weight: 600; line-height: 1.3; margin-bottom: .5rem; }
    .subtitle { font-size: 14px; color: #555; margin-bottom: 1.5rem; }
    .controls {
      display: flex; align-items: center; gap: 10px;
      margin-bottom: 1rem; flex-wrap: wrap;
    }
    .controls label {
      font-size: 12px; font-weight: 600; text-transform: uppercase;
      letter-spacing: .06em; color: #888;
    }
    .controls select {
      font-size: 13px; padding: 4px 10px; border: 1px solid #ccc;
      border-radius: 5px; color: #333; background: #fff; cursor: pointer;
    }
    .legend {
      display: flex; flex-wrap: wrap; gap: 14px;
      margin-bottom: 10px; font-size: 12px; color: #555;
    }
    .legend-item { display: flex; align-items: center; gap: 5px; }
    .legend-swatch { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
    .chart-wrapper { position: relative; width: 100%; height: 360px; }
    .table-caption {
      font-size: 12px; font-weight: 600; color: #555; margin: 1.5rem 0 0.5rem;
    }
    .table-section { overflow-x: auto; }
    #contracts-table { width: 100%; border-collapse: collapse; font-size: 12px; }
    #contracts-table th {
      text-align: left; padding: 5px 8px; border-bottom: 2px solid #ddd;
      font-weight: 600; color: #555; font-size: 11px; white-space: nowrap;
    }
    #contracts-table th.num { text-align: right; }
    #contracts-table td { padding: 5px 8px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }
    #contracts-table td.num { text-align: right; white-space: nowrap; font-weight: 600; }
    #contracts-table td.large { color: #c00; }
    #contracts-table tr:nth-child(even) { background: #fafafa; }
    #contracts-table a { color: #2563eb; text-decoration: none; }
    .source { font-size: 11px; color: #aaa; margin-top: 1.5rem; line-height: 1.5; }
    .source a { color: #aaa; }
    @media (max-width: 500px) { h1 { font-size: 18px; } }
  </style>
</head>

<body>
  <div class="container">
    <p class="eyebrow">Center for Western Priorities · DOI Contracting Analysis</p>
    <h1 id="chart-title">DOI urgency no-bid contracts by administration</h1>
    <p class="subtitle" id="chart-subtitle"></p>

    <div class="controls">
      <label for="agency-select">Agency:</label>
      <select id="agency-select"></select>
      <label for="admin-select">Admin:</label>
      <select id="admin-select"></select>
    </div>

    <div class="legend" id="legend"></div>

    <div class="chart-wrapper">
      <canvas id="chart" role="img"
        aria-label="Bar chart of DOI urgency no-bid contracts by administration">
      </canvas>
    </div>

    <p id="table-caption" class="table-caption"></p>
    <div class="table-section">
      <table id="contracts-table">
        <thead id="contracts-thead"></thead>
        <tbody id="contracts-tbody"></tbody>
      </table>
    </div>

    <p class="source">
      First <span id="window-days"></span> days per administration (Jan. 20 inauguration).
      Urgency (FAR 6.302-2) contracts only. Excludes statutory (AbilityOne/8(a)), utilities,
      sole-source (ONE/UNQ), and competed GSA Schedule orders (FAIR). Includes urgency task
      orders under IDV/GSA Schedule vehicles.
      Source: <a href="https://api.usaspending.gov">USASpending.gov</a> FPDS bulk download.
      Analysis: Center for Western Priorities.
    </p>
  </div>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
  <script>
  const DOI_DATA = /* __DOI_DATA__ */null/* end */;

  const ALL_DOI   = '__all__';
  const ALL_ADMIN = '__all__';

  function buildLabels(admin) {
    return admin === ALL_ADMIN ? DOI_DATA.administrations.slice() : [admin];
  }

  function buildDatasets(agency, admin) {
    const idxs = admin === ALL_ADMIN
      ? DOI_DATA.administrations.map((_, i) => i)
      : [DOI_DATA.administrations.indexOf(admin)];

    if (agency === ALL_DOI) {
      return Object.entries(DOI_DATA.doi_obligations).map(([name, vals]) => ({
        label: name,
        data: idxs.map(i => vals[i]),
        backgroundColor: DOI_DATA.agency_colors[name] || '#ccc',
      }));
    }
    const vals = DOI_DATA.doi_obligations[agency] || DOI_DATA.administrations.map(() => 0);
    return [{
      label: agency,
      data: idxs.map(i => vals[i]),
      backgroundColor: DOI_DATA.agency_colors[agency] || '#ccc',
    }];
  }

  function renderLegend(agency) {
    const el = document.getElementById('legend');
    let items;
    if (agency === ALL_DOI) {
      items = Object.entries(DOI_DATA.agency_colors).map(([name, color]) =>
        `<span class="legend-item"><span class="legend-swatch" style="background:${color}"></span>${name}</span>`
      );
    } else {
      const color = DOI_DATA.agency_colors[agency] || '#ccc';
      items = [`<span class="legend-item"><span class="legend-swatch" style="background:${color}"></span>${agency}</span>`];
    }
    el.innerHTML = items.join('');
  }

  function updateTitle(agency, admin) {
    const title = document.getElementById('chart-title');
    const sub   = document.getElementById('chart-subtitle');
    const wl    = DOI_DATA.window_label;
    const adminLabel = admin === ALL_ADMIN ? 'all administrations' : admin;
    if (agency === ALL_DOI) {
      title.textContent = 'DOI urgency no-bid contracts by administration';
      sub.textContent   = wl + ' · All Department of the Interior bureaus · ' + adminLabel;
    } else {
      title.textContent = agency + ' urgency no-bid contracts by administration';
      sub.textContent   = wl + ' · ' + adminLabel;
    }
  }

  function escHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function fmtAmount(amt) {
    return amt >= 1
      ? '$' + amt.toFixed(1) + 'M'
      : '$' + Math.round(amt * 1000) + 'K';
  }

  function renderTable(agency, admin) {
    const showAgency = agency === ALL_DOI;
    const showAdmin  = admin  === ALL_ADMIN;

    const filtered = DOI_DATA.contracts.filter(function(c) {
      return (showAgency || c.agency === agency) && (showAdmin || c.admin === admin);
    });

    let hdr = '<th class="num">Amount</th><th>Vendor</th><th>Description</th>';
    if (showAgency) hdr += '<th>Agency</th>';
    hdr += '<th>State</th><th>Date</th>';
    if (showAdmin)  hdr += '<th>Admin</th>';
    hdr += '<th></th>';
    document.getElementById('contracts-thead').innerHTML = '<tr>' + hdr + '</tr>';

    const rows = filtered.map(function(c) {
      const amtClass = 'num' + (c.amount >= 1 ? ' large' : '');
      let cells = `<td class="${amtClass}">${fmtAmount(c.amount)}</td>`
        + `<td>${escHtml(c.vendor)}</td>`
        + `<td style="color:#555">${escHtml(c.description)}</td>`;
      if (showAgency) cells += `<td style="color:#666">${escHtml(c.agency_short)}</td>`;
      cells += `<td style="color:#666">${escHtml(c.state)}</td>`
        + `<td style="color:#666;white-space:nowrap">${escHtml(c.date)}</td>`;
      if (showAdmin) cells += `<td style="color:#666;white-space:nowrap">${escHtml(c.admin)}</td>`;
      cells += `<td><a href="${escHtml(c.url)}" target="_blank" rel="noopener" title="USASpending">↗</a></td>`;
      return '<tr>' + cells + '</tr>';
    });
    document.getElementById('contracts-tbody').innerHTML = rows.join('');

    const agencyLabel = agency === ALL_DOI ? 'all agencies' : agency;
    const adminLabel  = admin  === ALL_ADMIN ? 'all administrations' : admin;
    document.getElementById('table-caption').textContent =
      filtered.length + ' urgency contracts · ' + agencyLabel + ' · ' + adminLabel;
  }

  function switchTo(agency, admin) {
    chart.data.labels   = buildLabels(admin);
    chart.data.datasets = buildDatasets(agency, admin);
    chart.update();
    renderLegend(agency);
    updateTitle(agency, admin);
    renderTable(agency, admin);
  }

  // Populate agency dropdown
  const select = document.getElementById('agency-select');
  [{ label: 'All DOI', value: ALL_DOI }]
    .concat(
      Object.keys(DOI_DATA.doi_obligations)
        .filter(a => a !== 'Other DOI bureaus')
        .map(a => ({ label: a, value: a }))
    )
    .forEach(function(item) {
      const opt = document.createElement('option');
      opt.value = item.value;
      opt.textContent = item.label;
      select.appendChild(opt);
    });
  select.addEventListener('change', function() { switchTo(this.value, adminSelect.value); });

  // Populate admin dropdown
  const adminSelect = document.getElementById('admin-select');
  [{ label: 'All administrations', value: ALL_ADMIN }]
    .concat(DOI_DATA.administrations.map(a => ({ label: a, value: a })))
    .forEach(function(item) {
      const opt = document.createElement('option');
      opt.value = item.value;
      opt.textContent = item.label;
      adminSelect.appendChild(opt);
    });
  adminSelect.addEventListener('change', function() { switchTo(select.value, this.value); });

  // Source note
  document.getElementById('window-days').textContent = DOI_DATA.days_in_window;

  // Init chart
  const chart = new Chart(document.getElementById('chart'), {
    type: 'bar',
    data: {
      labels: buildLabels(ALL_ADMIN),
      datasets: buildDatasets(ALL_DOI, ALL_ADMIN),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(ctx) {
              const v = ctx.parsed.y;
              if (Math.abs(v) < 0.005) return null;
              return ' ' + ctx.dataset.label + ': $' + v.toFixed(1) + 'M';
            },
            footer: function(items) {
              const total = items.reduce(function(s, i) { return s + i.parsed.y; }, 0);
              return 'Total: $' + total.toFixed(1) + 'M';
            }
          }
        }
      },
      scales: {
        x: {
          stacked: true,
          grid: { display: false },
          ticks: { font: { size: 13 }, color: '#444' }
        },
        y: {
          stacked: true,
          grid: { color: 'rgba(0,0,0,0.06)' },
          ticks: {
            font: { size: 11 },
            color: '#666',
            callback: function(v) { return '$' + v + 'M'; }
          },
          title: {
            display: true,
            text: 'Obligated ($ millions)',
            color: '#666',
            font: { size: 11 }
          }
        }
      }
    }
  });

  renderLegend(ALL_DOI);
  updateTitle(ALL_DOI, ALL_ADMIN);
  renderTable(ALL_DOI, ALL_ADMIN);
  </script>
</body>
</html>
```

- [ ] **Step 2: Commit the template**

```bash
git add doi_viz_template.html
git commit -m "Rewrite doi_viz_template.html: urgency-only, admin dropdown, contract table"
```

---

## Task 5: Regenerate `doi_viz.html` and verify

**Files:**
- Regenerate: `doi_viz.html`

- [ ] **Step 1: Run the build script**

```bash
cd /Users/aaronweiss/python-projects/doi-contracts && source .venv/bin/activate
python build_doi_viz.py
```

Expected output (numbers approximate):
```
Loaded N,NNN DOI urgency transactions, NNN unique awards
Agencies in viz (N): ['National Park Service', 'Bureau of Land Management', ...]
  Trump I: $X.XM urgency total
  Biden: $X.XM urgency total
  Trump II: $XX.XM urgency total
  Contracts in table: NNN
Wrote doi_viz.html
```

Trump II total should be substantially larger than Trump I and Biden.

- [ ] **Step 2: Open `doi_viz.html` in a browser and verify all four filter states**

Open `doi_viz.html` in a browser (no server needed — it's a static file).

Check **Admin: All, Agency: All DOI:**
- Chart shows 3 bars stacked by agency, Trump II tallest
- Agency dropdown shows individual bureau names (no "Other DOI bureaus" option)
- Table shows all urgency contracts across all admins, sorted by amount desc
- Table has Agency and Admin columns
- First row should be the $14.65M Atlantic Industrial Coatings NPS contract

Check **Admin: Trump II, Agency: All DOI:**
- Chart shows exactly 1 bar (Trump II only, other bars gone)
- Table shows only Trump II contracts, sorted by amount desc
- Table has Agency column, no Admin column

Check **Admin: All, Agency: National Park Service:**
- Chart shows 3 solid red bars (NPS color), Trump II tallest
- Legend shows single NPS swatch
- Table shows NPS contracts from all admins
- Table has Admin column, no Agency column

Check **Admin: Trump II, Agency: National Park Service:**
- Chart shows 1 solid red bar
- Table shows NPS Trump II contracts only
- ↗ link on first row opens USASpending page for that award
- Table has neither Agency nor Admin column

- [ ] **Step 3: Commit**

```bash
git add doi_viz.html
git commit -m "Regenerate doi_viz.html: urgency-only, admin+agency filters, contract table"
```

---

## Done

Run the full test suite one final time to confirm nothing regressed:

```bash
pytest -v
```

All tests should pass.
