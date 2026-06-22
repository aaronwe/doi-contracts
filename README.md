# NPS No-Bid Contract Analysis

Data pipeline and analysis scripts comparing National Park Service sole-source (other-than-full-and-open-competition) contracts across four administrations using the [USASpending.gov API](https://api.usaspending.gov).

## What this is

Federal agencies are generally required to compete contracts. When they don't, they must cite a legal justification under FAR Part 6. This project tracks NPS's use of those no-bid contracts — and compares the current administration's pace to prior ones for an equal number of days in office.

**Trigger:** An urgency-justified sole-source contract for the Lincoln Memorial Reflecting Pool ([CONT_AWD_140P2026C0028_1443](https://www.usaspending.gov/award/CONT_AWD_140P2026C0028_1443_-NONE-_-NONE-)), citing FAR 6.302-2 (Unusual and Compelling Urgency).

## Key findings (as of June 22, 2026 — first 519 days)

| Administration | Unique contracts | Total obligated | Median contract | Top justification |
|---|---|---|---|---|
| Trump II | 714 | $160M | $11,852 | Only One Source (FAR 6.302-1) |
| Biden | 981 | $222M | $8,807 | Authorized by Statute (FAR 6.302-5) |
| Trump I | 1,277 | $140M | $6,834 | Authorized by Statute |
| Obama I | 3,071 | $264M | $5,732 | Authorized by Statute |

**Urgency contracts (FAR 6.302-2) specifically:**

| Administration | Urgency contracts | Total obligated | Avg per contract |
|---|---|---|---|
| Trump II | 73 | $19.6M | ~$268k |
| Biden | 65 | $1.8M | ~$27k |
| Trump I | 59 | $0.75M | ~$13k |
| Obama I | 121 | $11.3M | ~$93k |

Trump II has more urgency-justified contracts than Biden or Trump I, and the per-contract dollar value is roughly 10× Biden's.

## Data

- **`nps_no_bid_contracts.csv`** — 28,988 transactions / 13,796 unique awards, 2009-01-20 through 2026-06-20. One row per FPDS transaction (original award + each modification).
- **`admin_comparison.csv`** — Aggregated comparison table, first 519 days per administration.

### Scope

- Agency: National Park Service (FPDS subtier code `1443`, under DOI)
- Competition filter: `extent_competed_code` in `{B, C}` — "Not Available for Competition" and "Not Competed"
- Award types: A, B, C, D (all contract types; excludes grants, loans, IDVs)
- Date field: `action_date`
- Source: USASpending bulk download API, transaction-level FPDS data

### Key CSV columns

| Column | Description |
|---|---|
| `contract_award_unique_key` | Unique identifier per award (use to deduplicate transactions) |
| `contract_transaction_unique_key` | Unique identifier per transaction/modification |
| `award_id_piid` | Contract number |
| `action_date` | Date of this obligation action |
| `federal_action_obligation` | Dollars obligated in this transaction (can be negative) |
| `extent_competed_code` | `B` = Not Available for Competition; `C` = Not Competed |
| `other_than_full_and_open_competition_code` | Justification: `URG`=Urgency, `ONE`=Only One Source, `OTH`=Authorized by Statute, etc. |
| `other_than_full_and_open_competition` | Human-readable justification label |
| `recipient_name` | Contractor name |
| `primary_place_of_performance_state_code` | State where work performed |

## Usage

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Pull all NPS no-bid contracts (2009–present). ~20 min first run; instant on re-run.
python fetch_contracts.py

# Compare first-N-days across administrations. N auto-updates to today.
python compare_admins.py
```

Re-running `fetch_contracts.py` refreshes only the current year; all prior years are cached in `downloads/` (not committed — regenerate as needed).

## Methodological notes

- **Transaction vs. award level:** The CSV is transaction-level (one row per FPDS action). A contract with modifications appears on multiple rows. `compare_admins.py` deduplicates on `contract_award_unique_key` for counts and sums `federal_action_obligation` for dollar totals.
- **Comparison window:** Each administration's window starts on inauguration day and runs for the same number of elapsed days as Trump II has been in office on the day you run `compare_admins.py`. The window updates automatically.
- **Label changes:** FPDS description strings changed between administrations (e.g., "URGENCY" vs "URGENCY (FAR 6.302-2)"), so group by `_code` columns for longitudinal comparisons, not the human-readable labels.
- **2026 data:** USASpending data extends through mid-2026. Trump II's window therefore includes both 2025 and 2026 records.
