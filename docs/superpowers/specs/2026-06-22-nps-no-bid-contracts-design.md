# NPS No-Bid Contracts Analysis — Design Spec

**Date:** 2026-06-22  
**Status:** Approved

---

## Goal

Compare the volume and dollar value of no-bid (other-than-full-and-open-competition) contracts issued by the National Park Service across four administrations: Trump II, Biden, Trump I, and Obama I. Produce a primary CSV dataset and a like-for-like administration comparison.

---

## Outputs

| Artifact | Description |
|---|---|
| `nps_no_bid_contracts.csv` | All NPS other-than-full-and-open contracts from Jan 20, 2009 to present |
| `admin_comparison.csv` | Per-administration summary for the first N days in office (N = days Trump II has been in office as of run date) |

---

## Data Source

**USASpending API** — `POST /api/v2/search/spending_by_award/`  
Public, no API key required. Documentation: https://api.usaspending.gov/docs/endpoints

---

## Filters

| Filter | Value |
|---|---|
| Agency | `awarding_sub_agency_code = "1443"` (NPS FPDS subtier code — verified at runtime against `/api/v2/references/agency/`) |
| Extent competed | `extent_competed_type_codes`: `["B", "C"]` |
| Date range | `action_date` from 2009-01-20 to present, chunked by fiscal year |
| Award type | `award_type_codes`: contract types only (A, B, C, D) |

### Extent Competed Codes Reference (FPDS single-letter codes)

| Code | Meaning |
|---|---|
| A | Full and Open Competition (excluded) |
| B | Not Available for Competition ← **included** |
| C | Not Competed ← **included** |
| D | Full and Open Competition after Exclusion of Sources (excluded) |
| E | Follow On to Competed Action / FAR 6.302-1 (excluded) |
| F | Competed Under SAP (excluded) |
| G | Not Competed Under SAP (excluded — micro-purchases, low signal) |

The *reason* for non-competition (e.g., URG = Urgency/FAR 6.302-2, NSS = Sole Source) is captured in the `other_than_full_and_open_competition` field as data, not used as a filter — so all justification types are preserved in the CSV for downstream analysis.

---

## Fields Captured

| Field | Notes |
|---|---|
| `contract_award_unique_key` | Dedup key |
| `award_id_piid` | Contract number |
| `action_date` | Date of this obligation action |
| `period_of_performance_start_date` | |
| `period_of_performance_current_end_date` | |
| `award_amount` | Total award value |
| `total_obligated_amount` | Dollars obligated to date |
| `recipient_name` | Contractor name |
| `recipient_uei` | Unique Entity Identifier |
| `awarding_sub_agency_name` | Should always be "National Park Service" |
| `description` | Contract description |
| `extent_competed` | Human-readable competition status |
| `extent_competed_code` | Raw FPDS code (B, C, URG, etc.) |
| `other_than_full_and_open_competition` | Justification reason (e.g., "URGENCY") |
| `solicitation_procedures` | |
| `naics_code` | Industry classification |
| `naics_description` | |
| `product_or_service_code` | PSC code |
| `place_of_performance_city_name` | |
| `place_of_performance_state_code` | |

---

## Script Architecture

```
doi-contracts/
├── config.py            # Constants: NPS code, administration windows, API URL
├── fetch_contracts.py   # Primary: pulls master CSV from USASpending
├── compare_admins.py    # Secondary: reads CSV, produces comparison table
└── requirements.txt     # requests, pandas
```

### `config.py`

Defines:
- `NPS_SUBTIER_CODE = "1443"`
- `EXTENT_COMPETED_CODES = ["B", "C", "CDO", "NDT", "NSS", "OTH", "SOL", "URG"]`
- Administration inauguration dates:
  - Trump II: 2025-01-20
  - Biden: 2021-01-20
  - Trump I: 2017-01-20
  - Obama I: 2009-01-20
- `OUTPUT_CSV = "nps_no_bid_contracts.csv"`
- `API_BASE = "https://api.usaspending.gov/api/v2"`

### `fetch_contracts.py`

1. Verify NPS subtier code: GET `/api/v2/references/agency/` and confirm "1443" maps to National Park Service; abort with a clear error if not found
2. Determine fiscal year range: FY2009 (starting 2009-01-20) through current FY
2. For each fiscal year:
   - Check if records for this FY already exist in `nps_no_bid_contracts.csv` (resumability)
   - POST to `/api/v2/search/spending_by_award/` with NPS + extent_competed + date filters
   - Paginate 100 records/page until exhausted
   - If a FY returns exactly 10,000 records: print warning and suggested bulk download command, continue
3. Deduplicate on `contract_award_unique_key`
4. Write `nps_no_bid_contracts.csv`

**Retry logic:** 3 attempts, exponential backoff (2s → 4s → 8s) on 429 or 5xx.

### `compare_admins.py`

1. Read `nps_no_bid_contracts.csv`
2. Compute `days_elapsed` = (today − 2025-01-20).days for Trump II window length
3. For each administration, filter rows where `action_date` falls within [inauguration_date, inauguration_date + days_elapsed]
4. Aggregate per administration:
   - `contract_count`
   - `total_obligated` (sum of `total_obligated_amount`)
   - `median_contract` (median of `total_obligated_amount`)
   - `top_justification` (most common `other_than_full_and_open_competition` value)
5. Output console table and `admin_comparison.csv`

---

## Administration Comparison Windows

Each window is `[inauguration_date, inauguration_date + N days]` where N = days Trump II has been in office on the day `compare_admins.py` is run. This makes the comparison automatically update as the administration continues.

| Administration | Inauguration | Window end (at 153 days) |
|---|---|---|
| Trump II | 2025-01-20 | 2025-06-22 |
| Biden | 2021-01-20 | 2021-06-22 |
| Trump I | 2017-01-20 | 2017-06-22 |
| Obama I | 2009-01-20 | 2009-06-22 |

---

## Error Handling

| Scenario | Behavior |
|---|---|
| 429 / 5xx from API | Retry 3x with 2s/4s/8s backoff, then raise |
| FY returns exactly 10,000 records | Warn and print bulk download command; do not silently truncate |
| `nps_no_bid_contracts.csv` already exists | Skip already-fetched FYs (keyed on date range); append new ones |
| Missing field in API response | Fill with `None`; log warning |

---

## Fallback: Bulk Download

If the search API proves too slow or hits structural limits, switch to:
`POST /api/v2/bulk_download/awards/` with the same filters. This is an async endpoint — poll `/api/v2/bulk_download/status/` until complete, then download and unzip the CSV.

---

## Dependencies

```
requests>=2.31.0
pandas>=2.0.0
```

No API key required.
