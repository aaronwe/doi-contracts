# Urgency-Only Visualization Refocus

**Date:** 2026-06-23
**Scope:** Refocus NPS and DOI no-bid contract visualizations to show only urgency-justified (FAR 6.302-2) contracts. Add a contract table and dual filters to the DOI viz.

---

## Background

The current visualizations show all discretionary no-bid contracts split by justification bucket (Urgency, Follow-on, Other). The Follow-on and Other categories contain a lot of defensible academic and routine spending that dilutes the story. Refocusing to urgency-only sharpens the comparison.

---

## NPS Viz (`viz.html`)

Static HTML file. Manual update only — no build script added.

### Changes

- **Remove stacked bar** → single solid-color bar per administration (one category, no stacking needed)
- **Update Chart.js datasets** from 3 datasets to 1: `Urgency (FAR 6.302-2)`, color `#E24B4A`
- **Update stat cards** to urgency-only counts (window: first 520 days):

  | Administration | Total | Contracts |
  |---|---|---|
  | Trump I | $1.353M | 55 |
  | Biden | $2.518M | 66 |
  | Trump II | $21.191M | 73 |

- **Update subtitle** to: "Urgency (FAR 6.302-2) no-bid contracts only · First 520 days"
- **Remove Follow-on and Other legend entries**
- **Update callout** to urgency-only framing (remove references to follow-on comparison)
- **Update source note** to remove follow-on/other exclusion language

---

## DOI Viz (`doi_viz_template.html` + `build_doi_viz.py`)

### Build Script Changes (`build_doi_viz.py`)

1. **Add urgency filter** in `load_contracts()` after existing exclusions:
   ```python
   is_urg = (
       (df["other_than_full_and_open_competition_code"] == URG_CODE) |
       (df["fair_opportunity_limited_sources_code"].fillna("") == URG_CODE)
   )
   df = df[is_urg]
   ```

2. **Remove `classify_justification()` and `aggregate_agency_breakdown()`** — no longer needed since there's only one justification category.

3. **`aggregate_doi_obligations()`** — no changes to function signature; now operates on urgency-only data automatically.

4. **Add `AGENCY_SHORT` dict** for compact table display:
   ```python
   AGENCY_SHORT = {
       "National Park Service": "NPS",
       "Bureau of Land Management": "BLM",
       "Bureau of Indian Affairs and Bureau of Indian Education": "BIA/BIE",
       "U.S. Fish and Wildlife Service": "FWS",
       "U.S. Geological Survey": "USGS",
       "Bureau of Reclamation": "BOR",
       "Bureau of Ocean Energy Management": "BOEM",
       "Office of Surface Mining, Reclamation and Enforcement": "OSMRE",
       "Bureau of Safety and Environmental Enforcement": "BSEE",
   }
   ```

5. **Add `build_contracts_table(df, admin_names, windows)`** — returns a flat list of urgency award rows across all administrations, sorted by `amount` descending. Each row:
   ```json
   {
     "piid": "140P2026C0028",
     "vendor": "ATLANTIC INDUSTRIAL COATINGS LLC",
     "description": "NAMA 291052 PAINT LINCOLN REFLECTING POOL",
     "agency": "NPS",
     "state": "DC",
     "date": "2026-03-12",
     "amount": 14.652,
     "url": "https://www.usaspending.gov/award/CONT_AWD_140P2026C0028_1443_-NONE-_-NONE-/",
     "admin": "Trump II"
   }
   ```
   Logic: for each admin window, find awards whose first transaction falls within the window, sum obligations, deduplicate to one row per `contract_award_unique_key`.

6. **Inject `contracts` array** into `DOI_DATA` alongside existing `doi_obligations`.

7. **Remove `agency_breakdown` from injected data** — no longer used by the template.

### Injected data shape (new)

```json
{
  "days_in_window": 520,
  "window_label": "First 520 days",
  "administrations": ["Trump I", "Biden", "Trump II"],
  "agency_colors": { "National Park Service": "#E24B4A", ... },
  "doi_obligations": { "National Park Service": [1.353, 2.518, 21.191], ... },
  "contracts": [ { ... }, ... ]
}
```

### Template Changes (`doi_viz_template.html`)

#### Controls

Add an administration dropdown alongside the existing agency dropdown:

```html
<div class="controls">
  <label for="agency-select">Agency:</label>
  <select id="agency-select">…</select>
  <label for="admin-select">Administration:</label>
  <select id="admin-select">
    <option value="__all__">All</option>
    <option value="Trump I">Trump I</option>
    <option value="Biden">Biden</option>
    <option value="Trump II">Trump II</option>
  </select>
</div>
```

#### Chart behavior

`switchTo(agency, admin)` rebuilds both `chart.data.labels` and `chart.data.datasets` on every filter change:

| Agency filter | Admin filter | Labels | Datasets |
|---|---|---|---|
| All DOI | All | `["Trump I","Biden","Trump II"]` | one dataset per agency, stacked |
| All DOI | Trump II | `["Trump II"]` | one dataset per agency, stacked, single value |
| NPS | All | `["Trump I","Biden","Trump II"]` | single NPS dataset, color = `DOI_DATA.agency_colors["National Park Service"]` |
| NPS | Trump II | `["Trump II"]` | single NPS dataset, single value, same agency color |

When a specific admin is selected, `chart.data.labels` is set to `[admin]` and each dataset's `data` array has exactly one value — no null/zero trick. The other admins are fully absent from the chart.

#### Legend

No changes to legend rendering; the existing logic shows agency swatches in All-DOI mode and a single agency swatch in single-agency mode. Since there's only one justification category now, the justification-bucket legend (Urgency/Follow-on/Other) is removed entirely.

#### Contract table

Add below the chart. The table responds to both filters.

**Column visibility rules:**
- `Amount`, `Vendor`, `Description`, `State`, `Date`, `Link` — always shown
- `Agency` column — shown only when agency filter = All DOI (hidden when filtered to a single agency — redundant)
- `Admin` column — shown only when admin filter = All (hidden when filtered to a specific admin — redundant)

**Filtering:** JavaScript filters `DOI_DATA.contracts` by `admin` and `agency` fields matching current dropdown values. `__all__` matches everything.

**Sorting:** Always by `amount` descending (pre-sorted at build time; JS preserves order).

**Caption:** Dynamic string — e.g. "73 urgency contracts · NPS · Trump II"

**Link:** `↗` anchor to `row.url` (USASpending), opens in new tab.

---

## Files Changed

| File | Change type |
|---|---|
| `viz.html` | Manual update — urgency-only numbers, simplified chart |
| `doi_viz_template.html` | Admin dropdown, contract table, simplified chart logic |
| `build_doi_viz.py` | Urgency filter, remove breakdown aggregation, add contracts table builder |
| `doi_viz.html` | Regenerated by `python build_doi_viz.py` |

No new files. No changes to `fetch_contracts.py`, `compare_admins.py`, `config.py`, or `urgency_utils.py`.
