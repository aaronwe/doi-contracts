# CLAUDE.md

## Project

DOI/NPS no-bid contract analysis pipeline. Pulls transaction-level FPDS data from USASpending.gov for all Department of the Interior sole-source contracts (2009–present) and compares administrations, with a focus on urgency (FAR 6.302-2) contracting under Trump II.

## Files

| File | Purpose |
|---|---|
| `config.py` | All constants: agency codes, filter codes, administration dates, column list |
| `fetch_contracts.py` | Full pipeline entry point — downloads DOI contracts, filters, writes CSVs, then auto-runs `compare_admins` and `build_doi_viz` |
| `compare_admins.py` | Reads `nps_no_bid_contracts.csv`, computes per-administration stats for matching first-N-days windows, writes `admin_comparison.csv` |
| `build_doi_viz.py` | Reads `doi_no_bid_contracts.csv`, builds urgency-only aggregations per agency, injects into template, writes `doi_viz.html` |
| `analyze_urgency.py` | Ad hoc urgency analysis tools (NPS focus) |
| `fetch_justifications.py` | Downloads sole-source justification PDFs from SAM.gov |
| `urgency_utils.py` | Shared utilities for urgency analysis |
| `doi_viz_template.html` | Handlebars-style template for the DOI urgency viz; edit this, not `doi_viz.html` |
| `doi_viz.html` | Generated output — do not edit directly |
| `doi_no_bid_contracts.csv` | 131,479 transactions / 56,921 unique awards, all DOI bureaus, 2009-01-20 to 2026-06-23 |
| `nps_no_bid_contracts.csv` | NPS subset: 29,116 transactions / 13,830 unique awards |
| `admin_comparison.csv` | Top-line NPS comparison, first 522 days per administration (as of 2026-06-25) |
| `OBAMA.md` | Methodology note explaining why Obama is excluded from the urgency viz |
| `downloads/` | Cached year ZIPs from USASpending (not committed; ~80 MB, regenerated automatically) |

## USASpending API

- Bulk download endpoint: `POST /api/v2/bulk_download/awards/`
- Status poll: `GET /api/v2/download/status?file_name=<name>`
- **NPS subtier code:** `1443` (confirmed from FPDS contract URLs and `/api/v2/references/agency/`)
- **DOI toptier name:** must pass `"toptier_name": "Department of the Interior"` in the agencies filter — omitting it caused NPS to be incorrectly resolved to USDA in testing
- Bulk download is limited to 1 year per request (`date_range total days must be within a year`)
- Returns ALL DOI contract types; no-bid filtering happens locally on `extent_competed_code`
- The downloaded CSV is transaction-level (one row per FPDS action/modification)
- 297 columns total; `config.py` `KEEP_COLUMNS` selects the ~25 we need
- Current year ZIP is always re-fetched; prior years are cached in `downloads/`

## Key data decisions

- **No-bid filter codes:** `extent_competed_code` in `{"B", "C"}` — "Not Available for Competition" and "Not Competed". Does NOT include `G` (Not Competed Under SAP / micro-purchases).
- **Urgency filter:** `other_than_full_and_open_competition_code == "URG"` (FAR 6.302-2) or `fair_opportunity_limited_sources_code == "URG"` (urgency IDV task orders). The viz shows urgency-only; `compare_admins.py` shows broader discretionary no-bid.
- **Excluded justification codes:** `OTH` (Authorized by Statute / AbilityOne), `UT` (Utilities), `ONE` (Only One Source), `UNQ` (Unique Source) — non-discretionary or analytically indistinguishable from competition. `FAIR` (competed GSA Schedule orders miscoded as no-bid) is also excluded.
- **Dollar metric:** `federal_action_obligation` (per-transaction; can be negative for deobligations). Summing across all transactions for an award gives total obligated.
- **Comparison window:** First N days of each administration, where N = days Trump II has been in office on the run date. Defined dynamically.
- **Dedup:** `contract_award_unique_key` for unique contract counts; `contract_transaction_unique_key` for row-level dedup in the master CSV.
- **New awards vs. modifications:** "new award count" counts contracts whose first-ever transaction falls in the window — avoids inflating counts with modifications to prior-administration contracts.

## Why Obama is excluded from the urgency viz

Obama I and II are in `config.py` and the underlying data covers 2009–present, but both are excluded from `doi_viz.html`. See `OBAMA.md` for full details. Short version:

- **Obama I** ($29.9M DOI urgency in the equivalent window) is probably overstated due to a known FPDS miscoding problem: GAO-14-304 (2014) found ~45% of FY2010–2012 urgency contracts were miscoded — agencies were using simplified acquisition procedures on urgent timelines and labeling them FAR 6.302-2. FPDS issued corrective guidance in December 2014. There's no clean way to retroactively remove miscoded entries.
- **Obama II** ($11M) is on the post-correction footing and is consistent with Trump I ($13M) and Biden ($5M) — these three form a 12-year baseline before Trump II's spike to $31.8M. Including Obama II would add a data point that supports the story but also invites scrutiny of why Obama I is excluded.
- The cleanest, least-vulnerable comparison is Trump I / Biden / Trump II. The `obama-comparison` branch has a working five-administration version for internal reference.

## Running

```bash
source .venv/bin/activate
python fetch_contracts.py   # full pipeline: fetch → compare → build viz
                            # ~20 min first run; skips cached years on re-run
                            # always re-fetches current year
```

Running `compare_admins.py` or `build_doi_viz.py` directly still works for partial updates (e.g., rebuilding the viz without re-fetching data):

```bash
python compare_admins.py    # updates admin_comparison.csv from existing nps CSV
python build_doi_viz.py     # rebuilds doi_viz.html from existing doi CSV
```

## Extending

**To add more administrations to the viz:** add to `VIZ_ADMIN_NAMES` in `build_doi_viz.py` (currently `["Trump I", "Biden", "Trump II"]`) and ensure the name matches an entry in `config.py` `ADMINISTRATIONS`.

**To add more administrations to compare_admins:** add entries to `ADMINISTRATIONS` in `config.py`. Extend `DATA_START_DATE` as needed (API bulk download goes back to 2000-10-01).

**To change the agency:** update `NPS_SUBTIER_NAME` and `DOI_TOPTIER_NAME` in `config.py`. Verify the new subtier code appears in downloaded data via `awarding_sub_agency_code`.

**To add IDV/IDIQ task orders:** add `"PIID"` award type codes to `CONTRACT_AWARD_TYPES` (currently only A, B, C, D — definitive contracts and purchase orders).

**To re-run a specific year:** delete `downloads/doi_contracts_YYYY.zip`; `fetch_contracts.py` will re-fetch it. (Old `nps_contracts_YYYY.zip` files from a prior pipeline version are unused and can be deleted.)
