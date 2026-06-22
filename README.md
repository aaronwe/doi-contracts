# NPS No-Bid Contract Analysis

Data pipeline and analysis scripts comparing National Park Service sole-source (other-than-full-and-open-competition) contracts across four administrations using the [USASpending.gov API](https://api.usaspending.gov).

## What this is

Federal agencies are generally required to compete contracts. When they don't, they must cite a legal justification under FAR Part 6. This project tracks NPS's use of *discretionary* no-bid contracts — cases where the agency exercised judgment about whether to compete — and compares the current administration's pace to prior ones for an equal number of days in office.

**Trigger:** An urgency-justified sole-source contract for the Lincoln Memorial Reflecting Pool ([CONT_AWD_140P2026C0028_1443](https://www.usaspending.gov/award/CONT_AWD_140P2026C0028_1443_-NONE-_-NONE-)), citing FAR 6.302-2 (Unusual and Compelling Urgency).

## What counts as "discretionary no-bid"

Not all sole-source contracts reflect agency discretion. We include only justification codes where the agency made an affirmative choice to forgo competition:

**Included:**
| Code | FAR cite | Description |
|---|---|---|
| `URG` | 6.302-2 | Unusual and compelling urgency — time pressure that is often avoidable with planning |
| `FOC` | 6.302-1(a)(2) | Follow-on to a competed contract — can usually be re-competed |
| Others | various | Smaller codes (BND, STD, PI, MPT, PDR, etc.) |

**Excluded:**
| Code | FAR cite | Why excluded |
|---|---|---|
| `ONE` | 6.302-1 | Only one source — taking agencies at their word that no alternatives exist |
| `UNQ` | 6.302-1(b)(2) | Unique source — in practice indistinguishable from ONE; requires the same "unique need" showing and is used interchangeably by contracting officers |
| `OTH` | 6.302-5 | Authorized by statute — includes AbilityOne (mandated disability-employment nonprofits) and 8(a) Alaska Native Corporation set-asides; required by law |
| `UT` | 6.302-1(b)(3) | Utilities — regulated monopolies; NPS has no vendor choice |

**Administrations compared:** Trump II, Biden, Trump I. Obama I is excluded because the American Recovery and Reinvestment Act (stimulus) created an anomalous burst of small site-specific contracts in 2009–2010 that are not comparable to post-stimulus baselines.

The master CSV (`nps_no_bid_contracts.csv`) retains all codes. Filtering happens in `compare_admins.py`.

## Key findings (as of June 22, 2026 — first 519 days)

| Administration | Unique contracts | Total obligated | Median contract | Top justification |
|---|---|---|---|---|
| Trump II | 88 | $20.4M | $18,784 | Urgency (FAR 6.302-2) |
| Biden | 108 | $3.5M | $6,500 | Urgency (FAR 6.302-2) |
| Trump I | 118 | $5.2M | $6,594 | Follow-On Contract |

**Urgency contracts (FAR 6.302-2) specifically:**

| Administration | Urgency contracts | Total obligated | Avg per contract |
|---|---|---|---|
| Trump II | 73 | $19.6M | ~$269k |
| Biden | 65 | $1.8M | ~$27k |
| Trump I | 56 | $0.8M | ~$13k |

Trump II obligated $19.6M in urgency-justified contracts in the first 519 days — 5.8× Biden's total discretionary no-bid spending and 3.9× Trump I's. Urgency alone makes up 96% of Trump II's discretionary no-bid total, versus 50% for Biden and 14% for Trump I (where follow-on contracts dominate).

## Data

- **`nps_no_bid_contracts.csv`** — 28,988 transactions / 13,796 unique awards, 2009-01-20 through 2026-06-20. One row per FPDS transaction (original award + each modification). Includes all `extent_competed_code` B/C contracts; justification filtering happens in analysis scripts.
- **`admin_comparison.csv`** — Aggregated comparison table, first 519 days per administration, discretionary no-bid only.

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
| `other_than_full_and_open_competition_code` | Justification code: `URG`, `ONE`, `OTH`, `UT`, `FOC`, `UNQ`, etc. |
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
- **Justification code filtering:** The `EXCLUDE_JUSTIFICATION_CODES` set in `compare_admins.py` controls which codes are excluded. The master CSV retains everything; filtering is non-destructive.
- **Label changes:** FPDS description strings changed between administrations (e.g., "URGENCY" vs "URGENCY (FAR 6.302-2)"), so group by `_code` columns for longitudinal comparisons, not the human-readable labels.
- **2026 data:** USASpending data extends through mid-2026. Trump II's window therefore includes both 2025 and 2026 records.
