# Urgency Investigation Tool — Design Spec

**Date:** 2026-06-22  
**Status:** Approved

## Goal

Surface NPS no-bid contracts during the second Trump administration (2025-01-20 onward) that were justified using FAR 6.302-2 (urgency) but whose descriptions suggest the work was routine, cosmetic, or planned rather than genuinely urgent. The reflecting pool painting ($14.6M) is the known example; this tool finds more.

Output is an **investigation tool** for journalists, not a publication-ready piece. The table gives reporters raw evidence to pursue.

---

## Data Flow

```
nps_no_bid_contracts.csv
        │
        ▼
fetch_justifications.py  ──→  docs/justifications/{piid}/*.pdf
        │
        ▼
justifications_manifest.csv
        │
        ▼
analyze_urgency.py
        │
        ▼
urgency_investigation.md
```

`justifications_manifest.csv` is the resume checkpoint: `fetch_justifications.py` skips any PIID already present, so the run can be interrupted and restarted safely.

---

## Input

- `nps_no_bid_contracts.csv` — master transaction file (existing pipeline output)
- Filter: `action_date >= 2025-01-20` AND `other_than_full_and_open_competition_code == "URG"`
- Deduplicated to one row per `contract_award_unique_key` (sum obligations, take first `action_date`)

As of 2026-06-22: **72 unique URG awards** during Trump II.

---

## Script 1: `fetch_justifications.py`

### Behavior

For each unique award not already in `justifications_manifest.csv`:

1. Call `GET https://api.usaspending.gov/api/v2/awards/{contract_award_unique_key}/` to retrieve full award detail. The response includes `latest_transaction_contract_data` with competition/justification fields and a `solicitation_identifier` (SAM.gov notice number).
2. Construct three always-available links:
   - USASpending permalink: `https://www.usaspending.gov/award/{contract_award_unique_key}/`
   - SAM.gov PIID search: `https://sam.gov/search/?keywords={award_id_piid}&index=co`
   - SAM.gov solicitation search (when `solicitation_identifier` present): `https://sam.gov/search/?keywords={solicitation_identifier}&index=opp`
3. Attempt to download any J&A PDFs found via a SAM.gov free-text search of the award page (best-effort; most contracts will result in "Link only" since SAM.gov's document API requires a key and the FPDS Atom feed now redirects to SAM.gov HTML).
4. Append one row to `justifications_manifest.csv`

Note: confirmed via live API testing that (a) USASpending award detail does not return document URLs, and (b) the FPDS Atom feed (`fpds.gov/ezsearch/...?rss=1`) now returns SAM.gov HTML rather than XML. The `doc_local_path` column will be empty for most rows; the three link columns give journalists direct paths to find J&As manually.

### Rate limiting

~2 requests/second (0.5s sleep between calls) to avoid hammering the USASpending API.

### Output: `justifications_manifest.csv`

| Column | Description |
|---|---|
| `award_id_piid` | Contract PIID (primary key for resume check) |
| `contract_award_unique_key` | USASpending generated unique ID |
| `recipient_name` | Vendor name |
| `description` | `prime_award_base_transaction_description` |
| `total_obligation` | Sum of `federal_action_obligation` across all transactions |
| `first_action_date` | Earliest `action_date` for this award |
| `psc_description` | `product_or_service_code_description` |
| `state` | `primary_place_of_performance_state_code` |
| `usaspending_url` | Permalink |
| `fpds_search_url` | FPDS search URL |
| `doc_url` | Document URL from API (blank if not found) |
| `doc_local_path` | Relative path to downloaded file (blank if not downloaded) |

---

## Script 2: `analyze_urgency.py`

### Behavior

1. Read `nps_no_bid_contracts.csv`, filter/aggregate to Trump II URG awards
2. Join with `justifications_manifest.csv` on `award_id_piid`
3. Write `urgency_investigation.md`

### Output: `urgency_investigation.md`

**Header block** (auto-generated):
- Date range and administration
- Total URG contract count and total dollars
- Count with downloaded J&A docs / link only / not found

**Flat table** sorted by `total_obligation` descending:

| $ | PIID | Vendor | Description | Location | PSC | J&A | Links |
|---|---|---|---|---|---|---|---|

- `J&A` column values: `Downloaded`, `Link only`, or `Not found`
- `Links` column: markdown links — `[USASpending](url)` and `[FPDS](url)`
- Dollar amounts formatted as `$X,XXX,XXX`
- Descriptions truncated to ~120 chars

No filtering or scoring — all 72 URG awards appear. Sorted by dollar descending so the highest-value contracts (most newsworthy) lead.

---

## Running

```bash
source .venv/bin/activate
python fetch_justifications.py    # fetches API + downloads docs; resumable
python analyze_urgency.py         # instant; reads manifest + master CSV
```

---

## Future extensions

- Add `--piid` flag to `fetch_justifications.py` to re-fetch a single contract
- Extend to other `other_than_full_and_open_competition_code` values (not just URG)
- Add Obama/Trump I/Biden URG contracts for cross-administration comparison
