# DOI-Wide No-Bid Contracts Analysis — Design Spec

**Date:** 2026-06-22
**Status:** Approved

## Overview

Expand the existing NPS-only no-bid contracts analysis to cover all Department of the Interior bureaus. Produce a new interactive visualization (`doi_viz.html`) with a dropdown to view all DOI stacked by agency, or zoom into any single bureau to see its Urgency / Follow-on / Other breakdown. The NPS-only pipeline remains intact; NPS data is derived as a filtered subset of the DOI-wide download.

---

## Design Decisions

| Question | Decision |
|---|---|
| Output format | Hybrid: `build_doi_viz.py` generates a self-contained HTML file with pre-aggregated JSON baked in |
| Chart type (All DOI) | Stacked bar by sub-agency (Trump I / Biden / Trump II on X axis) |
| Chart type (single agency) | Stacked bar by justification type (Urgency / Follow-on / Other) — same palette as existing `viz.html` |
| Agency filter UI | Dropdown above the chart; "All DOI" is default |
| Data pipeline | DOI-wide primary (`doi_no_bid_contracts.csv`); NPS derived as filtered subset |
| Historical depth | `DATA_START_DATE = 2009-01-20` (Obama I inauguration) — unchanged |

---

## Files Changed

### Modified: `config.py`

- Rename `OUTPUT_CSV` → `DOI_OUTPUT_CSV = "doi_no_bid_contracts.csv"`
- Add `NPS_OUTPUT_CSV = "nps_no_bid_contracts.csv"` (derived subset)
- Remove `NPS_SUBTIER_NAME` from fetch filter (fetch is now DOI-wide); keep constant for NPS subset derivation
- Add Obama I and Obama II to `ADMINISTRATIONS` (data ready for future use; `compare_admins.py` can opt in when needed):
  ```python
  {"name": "Obama II", "inauguration": date(2013, 1, 20)},
  {"name": "Obama I",  "inauguration": date(2009, 1, 20)},
  ```
- `DATA_START_DATE` stays `date(2009, 1, 20)` — no change needed

### Modified: `fetch_contracts.py`

- Remove subtier filter from the `agencies` payload (keep only `toptier_name: "Department of the Interior"`)
- Write primary output to `DOI_OUTPUT_CSV`
- After concatenating all years, derive NPS subset: filter to `awarding_sub_agency_name == NPS_SUBTIER_NAME`, write to `NPS_OUTPUT_CSV`
- Rename cached ZIP files: `downloads/doi_contracts_YYYY.zip` (was `nps_contracts_YYYY.zip`)
- Update print statements / docstring to reflect DOI-wide scope

### Unchanged

- `compare_admins.py` — reads `nps_no_bid_contracts.csv`, no changes needed
- `viz.html` — NPS-only static viz, untouched
- `analyze_urgency.py`, `urgency_utils.py`, `fetch_justifications.py` — all read `nps_no_bid_contracts.csv`
- All tests

---

## New Files

### `doi_viz_template.html`

HTML template for the DOI-wide visualization. Contains a `/* __DOI_DATA__ */` marker inside a `<script>` block that `build_doi_viz.py` replaces with the pre-aggregated JSON assignment.

**Structure:**
- Eyebrow: "Center for Western Priorities · DOI Contracting Analysis"
- Title: dynamically updated via JS when agency changes (`"DOI discretionary no-bid contracts"` → `"NPS discretionary no-bid contracts"` etc.)
- Subtitle: updates to reflect selected agency name or "All Department of the Interior bureaus"
- Agency dropdown: options populated from `DOI_DATA.agencies` array; first option is "All DOI"
- Chart area: single `<canvas>` element driven by Chart.js (bundled or CDN)
- Legend: swaps between agency legend (All DOI) and justification legend (single agency)
- Source note: static text at the bottom

**Injection point:**
```html
<script>
const DOI_DATA = /* __DOI_DATA__ */null/* end */;
</script>
```

### `build_doi_viz.py`

Reads `doi_no_bid_contracts.csv`, applies exclusion logic, aggregates, and writes `doi_viz.html`.

**Exclusion logic** (same as `compare_admins.py`):
- Drop `other_than_full_and_open_competition_code` in `{OTH, UT, ONE, UNQ}`
- Drop `fair_opportunity_limited_sources_code == "FAIR"`
- Exempt IDV sole-source codes in `IDV_SOLE_SOURCE_FAIR_OPP_CODES` from the OTH exclusion

**Comparison window:** First N days per administration where N = days Trump II has been in office (same as `compare_admins.py`).

**Aggregation — All DOI view:**
```python
# Per agency, per administration: sum of federal_action_obligation
obligations[agency_name][admin_name] = float  # $ millions, rounded to 3dp
```
Agencies with < $100K total across all windows are rolled into `"Other DOI bureaus"`. Agency list sorted by Trump II obligations descending; "Other DOI bureaus" always last.

**Aggregation — single agency view:**
```python
# Per justification bucket, per administration
# Urgency: other_than_full_and_open_competition_code == "URG"
#          OR fair_opportunity_limited_sources_code == "URG" (IDV urgency task orders)
# Follow-on: exact code(s) to be confirmed from actual dataset values at implementation
#            time — likely other_than_full_and_open_competition_code values indicating
#            follow-on or brand-name justifications (inspect via value_counts() on the DOI CSV)
# Other: everything remaining after Urgency and Follow-on are separated
justification_buckets = {
    "Urgency (FAR 6.302-2)": <URG via otf code or fair_opp code>,
    "Follow-on contract":    <codes TBD from data — implement after first DOI fetch>,
    "Other":                 <remainder>,
}
agency_obligations[agency_name][bucket][admin_name] = float
```

**JSON output shape:**
```json
{
  "days_in_window": 519,
  "window_label": "First 519 days",
  "administrations": ["Trump I", "Biden", "Trump II"],
  "agency_colors": {
    "National Park Service": "#E24B4A",
    "Bureau of Land Management": "#EF9F27",
    "Bureau of Indian Affairs": "#4A90D9",
    "U.S. Fish and Wildlife Service": "#5BAD6F",
    "U.S. Geological Survey": "#9B59B6",
    "Other DOI bureaus": "#888780"
  },
  "doi_obligations": {
    "National Park Service": [5.8, 4.0, 22.5],
    "Bureau of Land Management": [12.3, 9.1, 31.4],
    "...": []
  },
  "agency_breakdown": {
    "National Park Service": {
      "Urgency (FAR 6.302-2)":  [1.3, 2.4, 21.2],
      "Follow-on contract":     [4.2, 1.2, 0.7],
      "Other":                  [0.3, 0.4, 0.6]
    },
    "Bureau of Land Management": { "...": [] }
  }
}
```

**Build step:**
```bash
python fetch_contracts.py   # ~20 min first run; writes doi_no_bid_contracts.csv + nps_no_bid_contracts.csv
python compare_admins.py    # unchanged
python build_doi_viz.py     # fast; writes doi_viz.html
```

### `doi_viz.html` (generated output)

Self-contained HTML file produced by `build_doi_viz.py`. Committed to git like `viz.html` — it is a publishable output intended for embedding in CWP articles.

---

## Viz Behavior

**On load:** "All DOI" selected. Chart shows stacked bars (one segment per bureau, ordered by Trump II size). Legend shows agency color swatches.

**On agency dropdown change:**
- If "All DOI": show `doi_obligations` dataset, agency legend, generic title
- If specific agency: show `agency_breakdown[agency]` dataset with Urgency / Follow-on / Other colors (`#E24B4A` / `#EF9F27` / `#888780`), justification legend, update title to `"[Agency short name] discretionary no-bid contracts"`

**Tooltip:** hover shows per-segment value + total footer (same pattern as `viz.html`).

---

## Out of Scope

- No changes to `compare_admins.py` to include Obama administrations (data is present; opt-in is a separate task)
- No `doi_comparison.csv` output — `build_doi_viz.py` is viz-only
- No Obama rows in the viz (Trump I / Biden / Trump II only, matching existing viz)
- No contract count metric toggle (dollars only)

---

## Open Questions (resolved)

- ~~Checkbox vs. dropdown filter~~ → Dropdown
- ~~Stack by justification vs. by agency~~ → By agency for All DOI; by justification for single agency
- ~~Static vs. data-driven~~ → Data-driven (build step injects JSON)
