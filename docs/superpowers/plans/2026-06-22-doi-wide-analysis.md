# DOI-Wide No-Bid Contracts Analysis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the NPS-only no-bid contract pipeline to cover all DOI bureaus and produce an interactive `doi_viz.html` with an agency dropdown that shows either the full DOI stacked by bureau or a single bureau's Urgency/Follow-on/Other breakdown.

**Architecture:** `fetch_contracts.py` is widened from NPS-subtier to DOI-toptier; it writes `doi_no_bid_contracts.csv` as the primary output and derives `nps_no_bid_contracts.csv` as a filtered subset so all existing downstream scripts continue to work unchanged. A new `build_doi_viz.py` reads the DOI CSV, aggregates obligations per-agency and per-justification-bucket, and injects a JSON blob into `doi_viz_template.html` to produce a self-contained `doi_viz.html`.

**Tech Stack:** Python 3, pandas, Chart.js 4.4.1 (CDN), pytest

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `config.py` | Rename `OUTPUT_CSV` → `DOI_OUTPUT_CSV`; add `NPS_OUTPUT_CSV`; add Obama I & II to `ADMINISTRATIONS` |
| Modify | `urgency_utils.py` | Update import from `OUTPUT_CSV` → `NPS_OUTPUT_CSV` |
| Modify | `compare_admins.py` | Update import from `OUTPUT_CSV` → `NPS_OUTPUT_CSV` |
| Modify | `fetch_contracts.py` | Pull all DOI (toptier only); write DOI CSV; derive NPS CSV; rename ZIPs |
| Create | `doi_viz_template.html` | Chart.js HTML template with `/* __DOI_DATA__ */null/* end */` injection marker |
| Create | `build_doi_viz.py` | Aggregate obligations; inject JSON into template; write `doi_viz.html` |
| Create | `tests/test_config.py` | Verify renamed constants and Obama entries |
| Create | `tests/test_fetch_contracts.py` | Verify DOI payload shape and NPS derivation function |
| Create | `tests/test_build_doi_viz.py` | Verify aggregation, classification, and injection logic |
| Commit | `doi_viz.html` | Generated publishable output |

---

## Task 1: Update config.py constants and fix downstream imports

**Files:**
- Modify: `config.py`
- Modify: `urgency_utils.py`
- Modify: `compare_admins.py`
- Create: `tests/test_config.py`

- [ ] **Step 1.1: Write the failing config tests**

Create `tests/test_config.py`:

```python
from datetime import date
import config


def test_doi_output_csv():
    assert config.DOI_OUTPUT_CSV == "doi_no_bid_contracts.csv"


def test_nps_output_csv():
    assert config.NPS_OUTPUT_CSV == "nps_no_bid_contracts.csv"


def test_output_csv_removed():
    assert not hasattr(config, "OUTPUT_CSV"), \
        "OUTPUT_CSV was renamed to DOI_OUTPUT_CSV and NPS_OUTPUT_CSV — remove the old name"


def test_administrations_includes_obama():
    names = [a["name"] for a in config.ADMINISTRATIONS]
    assert "Obama II" in names
    assert "Obama I" in names


def test_obama_inaugurations():
    admin_map = {a["name"]: a["inauguration"] for a in config.ADMINISTRATIONS}
    assert admin_map["Obama II"] == date(2013, 1, 20)
    assert admin_map["Obama I"] == date(2009, 1, 20)


def test_trump2_still_first_administration():
    assert config.ADMINISTRATIONS[0]["name"] == "Trump II"
    assert config.TRUMP2_START == config.ADMINISTRATIONS[0]["inauguration"]
```

- [ ] **Step 1.2: Run to confirm they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `FAILED` — `DOI_OUTPUT_CSV` does not exist yet.

- [ ] **Step 1.3: Update config.py**

In `config.py`, replace line 42:
```python
OUTPUT_CSV = "nps_no_bid_contracts.csv"
```
with:
```python
DOI_OUTPUT_CSV = "doi_no_bid_contracts.csv"
NPS_OUTPUT_CSV = "nps_no_bid_contracts.csv"
```

Add Obama II and Obama I to `ADMINISTRATIONS` (after Trump I, before closing bracket):
```python
ADMINISTRATIONS = [
    {"name": "Trump II",  "inauguration": date(2025, 1, 20)},
    {"name": "Biden",     "inauguration": date(2021, 1, 20)},
    {"name": "Trump I",   "inauguration": date(2017, 1, 20)},
    {"name": "Obama II",  "inauguration": date(2013, 1, 20)},
    {"name": "Obama I",   "inauguration": date(2009, 1, 20)},
]
```

- [ ] **Step 1.4: Fix urgency_utils.py import**

In `urgency_utils.py`, line 4, change:
```python
from config import OUTPUT_CSV, TRUMP2_START, URG_CODE
```
to:
```python
from config import NPS_OUTPUT_CSV, TRUMP2_START, URG_CODE
```

And on line 7, change the function signature default:
```python
def load_trump2_urg_awards(master_csv: str = OUTPUT_CSV) -> pd.DataFrame:
```
to:
```python
def load_trump2_urg_awards(master_csv: str = NPS_OUTPUT_CSV) -> pd.DataFrame:
```

- [ ] **Step 1.5: Fix compare_admins.py import**

In `compare_admins.py`, line 60, change:
```python
from config import ADMINISTRATIONS, OUTPUT_CSV, COMPARISON_CSV, IDV_SOLE_SOURCE_FAIR_OPP_CODES
```
to:
```python
from config import ADMINISTRATIONS, NPS_OUTPUT_CSV, COMPARISON_CSV, IDV_SOLE_SOURCE_FAIR_OPP_CODES
```

On line 170, change:
```python
    df = load_contracts(OUTPUT_CSV)
```
to:
```python
    df = load_contracts(NPS_OUTPUT_CSV)
```

- [ ] **Step 1.6: Run all tests**

```bash
pytest -v
```

Expected: all tests pass. The `test_output_csv_removed` test now passes because `OUTPUT_CSV` no longer exists. Existing urgency utils tests pass because they pass an explicit `tmp_path` CSV and never rely on the default parameter value.

- [ ] **Step 1.7: Commit**

```bash
git add config.py urgency_utils.py compare_admins.py tests/test_config.py
git commit -m "Rename OUTPUT_CSV to DOI_OUTPUT_CSV/NPS_OUTPUT_CSV; add Obama entries to ADMINISTRATIONS"
```

---

## Task 2: Update fetch_contracts.py for DOI-wide downloads

**Files:**
- Modify: `fetch_contracts.py`
- Create: `tests/test_fetch_contracts.py`

- [ ] **Step 2.1: Write failing tests**

Create `tests/test_fetch_contracts.py`:

```python
import pandas as pd
from datetime import date

from fetch_contracts import _build_download_payload, derive_nps_subset
from config import DOI_TOPTIER_NAME, NPS_SUBTIER_NAME, CONTRACT_AWARD_TYPES


def test_payload_uses_toptier_doi():
    payload = _build_download_payload(date(2025, 1, 20), date(2025, 12, 31))
    agencies = payload["filters"]["agencies"]
    assert len(agencies) == 1
    assert agencies[0]["tier"] == "toptier"
    assert agencies[0]["name"] == DOI_TOPTIER_NAME
    assert "subtier" not in str(agencies[0])


def test_payload_has_no_subtier_name_field():
    payload = _build_download_payload(date(2025, 1, 20), date(2025, 12, 31))
    agency = payload["filters"]["agencies"][0]
    assert "toptier_name" not in agency


def test_payload_date_range():
    payload = _build_download_payload(date(2025, 1, 20), date(2025, 6, 30))
    dr = payload["filters"]["date_range"]
    assert dr["start_date"] == "2025-01-20"
    assert dr["end_date"] == "2025-06-30"


def test_payload_includes_all_award_types():
    payload = _build_download_payload(date(2025, 1, 20), date(2025, 12, 31))
    assert payload["filters"]["prime_award_types"] == CONTRACT_AWARD_TYPES


def test_derive_nps_subset_keeps_only_nps():
    df = pd.DataFrame({
        "awarding_sub_agency_name": [NPS_SUBTIER_NAME, "Bureau of Land Management", NPS_SUBTIER_NAME],
        "contract_transaction_unique_key": ["T1", "T2", "T3"],
        "federal_action_obligation": [100.0, 200.0, 300.0],
    })
    result = derive_nps_subset(df)
    assert len(result) == 2
    assert set(result["contract_transaction_unique_key"]) == {"T1", "T3"}


def test_derive_nps_subset_returns_copy():
    df = pd.DataFrame({
        "awarding_sub_agency_name": [NPS_SUBTIER_NAME],
        "contract_transaction_unique_key": ["T1"],
        "federal_action_obligation": [100.0],
    })
    result = derive_nps_subset(df)
    result["federal_action_obligation"] = 999.0
    assert df.iloc[0]["federal_action_obligation"] == 100.0
```

- [ ] **Step 2.2: Run to confirm they fail**

```bash
pytest tests/test_fetch_contracts.py -v
```

Expected: `ImportError` — `_build_download_payload` and `derive_nps_subset` do not exist yet.

- [ ] **Step 2.3: Refactor fetch_contracts.py imports and add helper functions**

Replace the import block at the top of `fetch_contracts.py` (lines 26–37):

```python
from config import (
    API_BASE,
    NPS_SUBTIER_NAME,
    DOI_TOPTIER_NAME,
    CONTRACT_AWARD_TYPES,
    NO_BID_CODES,
    IDV_SOLE_SOURCE_FAIR_OPP_CODES,
    DATA_START_DATE,
    DOI_OUTPUT_CSV,
    NPS_OUTPUT_CSV,
    DOWNLOADS_DIR,
    KEEP_COLUMNS,
)
```

Add these two functions after the `_post_with_retry` function (before `request_download`):

```python
def _build_download_payload(start_date: date, end_date: date) -> dict:
    return {
        "filters": {
            "prime_award_types": CONTRACT_AWARD_TYPES,
            "agencies": [
                {
                    "type": "awarding",
                    "tier": "toptier",
                    "name": DOI_TOPTIER_NAME,
                }
            ],
            "date_type": "action_date",
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        },
        "file_format": "csv",
    }


def derive_nps_subset(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["awarding_sub_agency_name"] == NPS_SUBTIER_NAME].copy()
```

- [ ] **Step 2.4: Update request_download to use the new helper**

Replace the `request_download` function body:

```python
def request_download(start_date: date, end_date: date) -> dict:
    payload = _build_download_payload(start_date, end_date)
    return _post_with_retry(f"{API_BASE}/bulk_download/awards/", payload)
```

- [ ] **Step 2.5: Update main() to use new output paths and derive NPS subset**

In `main()`, change the ZIP filename (line ~165):
```python
        zip_path = os.path.join(DOWNLOADS_DIR, f"doi_contracts_{year}.zip")
```

Replace the final write block (lines ~192–196):
```python
    combined.to_csv(DOI_OUTPUT_CSV, index=False)
    print(f"\nWrote {len(combined):,} transactions → {DOI_OUTPUT_CSV}")
    print(f"Unique awards: {combined['contract_award_unique_key'].nunique():,}")
    print(f"Date range: {combined['action_date'].min()} to {combined['action_date'].max()}")

    nps = derive_nps_subset(combined)
    nps.to_csv(NPS_OUTPUT_CSV, index=False)
    print(f"Derived NPS subset: {len(nps):,} transactions → {NPS_OUTPUT_CSV}")
    print(f"NPS unique awards: {nps['contract_award_unique_key'].nunique():,}")
```

Also update the docstring at the top of `main()` (or the module docstring) to say "DOI" instead of "NPS" and reference both output files.

- [ ] **Step 2.6: Run all tests**

```bash
pytest -v
```

Expected: all pass including the new `test_fetch_contracts.py` tests.

- [ ] **Step 2.7: Commit**

```bash
git add fetch_contracts.py tests/test_fetch_contracts.py
git commit -m "Update fetch_contracts.py to pull all DOI; derive NPS subset from DOI data"
```

---

## Task 3: Create doi_viz_template.html

**Files:**
- Create: `doi_viz_template.html`

No automated tests — verified visually after `build_doi_viz.py` generates `doi_viz.html` in Task 4.

- [ ] **Step 3.1: Create the template**

Create `doi_viz_template.html` with this content:

```html
<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DOI Discretionary No-Bid Contracts by Administration</title>
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
      display: flex; align-items: center; gap: 10px; margin-bottom: 1rem;
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
    .source { font-size: 11px; color: #aaa; margin-top: 1rem; line-height: 1.5; }
    .source a { color: #aaa; }
    @media (max-width: 500px) { h1 { font-size: 18px; } }
  </style>
</head>

<body>
  <div class="container">
    <p class="eyebrow">Center for Western Priorities · DOI Contracting Analysis</p>
    <h1 id="chart-title">DOI discretionary no-bid contracts by administration</h1>
    <p class="subtitle" id="chart-subtitle"></p>

    <div class="controls">
      <label for="agency-select">Agency:</label>
      <select id="agency-select"></select>
    </div>

    <div class="legend" id="legend"></div>

    <div class="chart-wrapper">
      <canvas id="chart" role="img"
        aria-label="Stacked bar chart of DOI discretionary no-bid contracts by administration">
      </canvas>
    </div>

    <p class="source">
      First <span id="window-days"></span> days per administration (Jan. 20 inauguration).
      Excludes statutory (AbilityOne/8(a)), utilities, sole-source (ONE/UNQ),
      and competed GSA Schedule orders (FAIR). Includes urgency and follow-on task orders
      under IDV/GSA Schedule vehicles.
      Source: <a href="https://api.usaspending.gov">USASpending.gov</a> FPDS bulk download.
      Analysis: Center for Western Priorities.
    </p>
  </div>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
  <script>
  const DOI_DATA = /* __DOI_DATA__ */null/* end */;

  const ALL_DOI = '__all__';
  const JUST_COLORS = {
    'Urgency (FAR 6.302-2)': '#E24B4A',
    'Follow-on contract':    '#EF9F27',
    'Other':                 '#888780',
  };
  const JUST_ORDER = ['Urgency (FAR 6.302-2)', 'Follow-on contract', 'Other'];

  function buildDatasets(agency) {
    if (agency === ALL_DOI) {
      return Object.entries(DOI_DATA.doi_obligations).map(([name, vals]) => ({
        label: name,
        data: vals,
        backgroundColor: DOI_DATA.agency_colors[name] || '#ccc',
      }));
    }
    const breakdown = DOI_DATA.agency_breakdown[agency];
    return JUST_ORDER.map(bucket => ({
      label: bucket,
      data: (breakdown && breakdown[bucket]) || DOI_DATA.administrations.map(() => 0),
      backgroundColor: JUST_COLORS[bucket],
    }));
  }

  function renderLegend(agency) {
    const el = document.getElementById('legend');
    let items;
    if (agency === ALL_DOI) {
      items = Object.entries(DOI_DATA.agency_colors).map(([name, color]) =>
        `<span class="legend-item"><span class="legend-swatch" style="background:${color}"></span>${name}</span>`
      );
    } else {
      items = JUST_ORDER.map(bucket =>
        `<span class="legend-item"><span class="legend-swatch" style="background:${JUST_COLORS[bucket]}"></span>${bucket}</span>`
      );
    }
    el.innerHTML = items.join('');
  }

  function updateTitle(agency) {
    const title = document.getElementById('chart-title');
    const sub = document.getElementById('chart-subtitle');
    const wl = DOI_DATA.window_label;
    if (agency === ALL_DOI) {
      title.textContent = 'DOI discretionary no-bid contracts by administration';
      sub.textContent = wl + ' · All Department of the Interior bureaus · Urgency, follow-on, and other discretionary no-bid contracts';
    } else {
      title.textContent = agency + ' discretionary no-bid contracts by administration';
      sub.textContent = wl + ' · Urgency, follow-on, and other discretionary no-bid contracts';
    }
  }

  function switchTo(agency) {
    chart.data.datasets = buildDatasets(agency);
    chart.update();
    renderLegend(agency);
    updateTitle(agency);
  }

  // Populate dropdown
  const select = document.getElementById('agency-select');
  select.innerHTML = '<option value="' + ALL_DOI + '">All DOI</option>' +
    Object.keys(DOI_DATA.doi_obligations)
      .map(a => '<option value="' + a + '">' + a + '</option>')
      .join('');
  select.addEventListener('change', function() { switchTo(this.value); });

  // Source note
  document.getElementById('window-days').textContent = DOI_DATA.days_in_window;

  // Init chart
  const chart = new Chart(document.getElementById('chart'), {
    type: 'bar',
    data: {
      labels: DOI_DATA.administrations,
      datasets: buildDatasets(ALL_DOI),
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
              if (v < 0.005) return null;
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
  updateTitle(ALL_DOI);
  </script>
</body>
</html>
```

- [ ] **Step 3.2: Commit**

```bash
git add doi_viz_template.html
git commit -m "Add doi_viz_template.html with agency dropdown and dual chart-state logic"
```

---

## Task 4: Create build_doi_viz.py

**Files:**
- Create: `build_doi_viz.py`
- Create: `tests/test_build_doi_viz.py`

- [ ] **Step 4.1: Explore follow-on justification codes in existing NPS data**

Run this to see what codes are actually in the current CSV after exclusions are applied — this tells you what codes map to "Follow-on contract" before the DOI-wide fetch is available:

```bash
python -c "
import pandas as pd
df = pd.read_csv('nps_no_bid_contracts.csv', dtype=str)
excl = {'OTH', 'UT', 'ONE', 'UNQ'}
df = df[~df['other_than_full_and_open_competition_code'].isin(excl)]
df = df[df['fair_opportunity_limited_sources_code'].fillna('') != 'FAIR']
print('=== other_than_full_and_open_competition_code ===')
print(df['other_than_full_and_open_competition_code'].value_counts().head(20))
print()
print('=== fair_opportunity_limited_sources_code ===')
print(df['fair_opportunity_limited_sources_code'].value_counts().head(20))
"
```

Examine the output. In `build_doi_viz.py` below, `FOLLOW_ON_OTF_CODES` and `FOLLOW_ON_FAIR_OPP_CODES` are seeded with the most likely codes (`FOO` for both). Update these sets based on what you find — any code that is clearly "follow-on work under a previously competed contract" should be included. `URG` is already the Urgency bucket; everything else after Follow-on codes are pulled out becomes "Other".

- [ ] **Step 4.2: Write the failing tests**

Create `tests/test_build_doi_viz.py`:

```python
import json
import pandas as pd
import pytest
from datetime import date, timedelta

from build_doi_viz import (
    INJECTION_MARKER,
    JUST_FOLLOWON,
    JUST_OTHER,
    JUST_URGENCY,
    classify_justification,
    inject_and_write,
    aggregate_doi_obligations,
    aggregate_agency_breakdown,
    compute_window,
    VIZ_ADMIN_NAMES,
)


# ── classify_justification ───────────────────────────────────────────────────

def test_classify_urg_via_otf_code():
    assert classify_justification("URG", "") == JUST_URGENCY


def test_classify_urg_via_fair_opp_code():
    # IDV urgency task order: OTH extent but URG fair_opp
    assert classify_justification("OTH", "URG") == JUST_URGENCY


def test_classify_followon_via_otf_code():
    assert classify_justification("FOO", "") == JUST_FOLLOWON


def test_classify_followon_via_fair_opp_code():
    assert classify_justification("", "FOO") == JUST_FOLLOWON


def test_classify_other_for_unknown_code():
    assert classify_justification("B", "") == JUST_OTHER


def test_classify_other_for_empty_codes():
    assert classify_justification("", "") == JUST_OTHER


def test_classify_urgency_takes_priority_over_followon():
    # If somehow both URG and FOO appear, URG wins
    assert classify_justification("URG", "FOO") == JUST_URGENCY


# ── inject_and_write ─────────────────────────────────────────────────────────

def test_inject_replaces_marker(tmp_path):
    template = tmp_path / "tmpl.html"
    output = tmp_path / "out.html"
    template.write_text(
        f"<script>const D = {INJECTION_MARKER};</script>", encoding="utf-8"
    )
    data = {"days_in_window": 100, "administrations": ["Trump I", "Biden"]}
    inject_and_write(data, str(template), str(output))

    content = output.read_text(encoding="utf-8")
    assert INJECTION_MARKER not in content
    assert '"days_in_window": 100' in content
    assert '"administrations"' in content


def test_inject_result_is_valid_js(tmp_path):
    template = tmp_path / "tmpl.html"
    output = tmp_path / "out.html"
    template.write_text(
        f"const D = {INJECTION_MARKER};", encoding="utf-8"
    )
    data = {"key": "value with 'quotes' and \"double\""}
    inject_and_write(data, str(template), str(output))
    content = output.read_text(encoding="utf-8")
    # The injected JSON should be parseable
    start = content.index("const D = ") + len("const D = ")
    end = content.index(";", start)
    parsed = json.loads(content[start:end])
    assert parsed["key"] == data["key"]


def test_inject_raises_if_marker_missing(tmp_path):
    template = tmp_path / "tmpl.html"
    output = tmp_path / "out.html"
    template.write_text("<script>const D = null;</script>", encoding="utf-8")
    with pytest.raises(ValueError, match="Injection marker"):
        inject_and_write({}, str(template), str(output))


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_df(rows):
    """rows: list of (date_str, agency, obligation, otf_code, fair_code)"""
    return pd.DataFrame([
        {
            "action_date": pd.Timestamp(r[0]),
            "awarding_sub_agency_name": r[1],
            "federal_action_obligation": float(r[2]),
            "other_than_full_and_open_competition_code": r[3],
            "fair_opportunity_limited_sources_code": r[4],
            "contract_award_unique_key": f"AWD-{i}",
        }
        for i, r in enumerate(rows)
    ])


def _windows_for(admin_names, days=365):
    base = {"Trump I": date(2017, 1, 20), "Biden": date(2021, 1, 20), "Trump II": date(2025, 1, 20)}
    return {
        name: (pd.Timestamp(base[name]), pd.Timestamp(base[name]) + pd.Timedelta(days=days - 1))
        for name in admin_names
    }


# ── aggregate_doi_obligations ────────────────────────────────────────────────

def test_aggregate_sums_by_agency_and_admin():
    df = _make_df([
        ("2025-02-01", "Agency A", 1_000_000, "URG", ""),
        ("2025-02-01", "Agency A", 2_000_000, "URG", ""),
        ("2025-02-01", "Agency B",   500_000, "URG", ""),
    ])
    windows = _windows_for(["Trump II"])
    result = aggregate_doi_obligations(df, ["Trump II"], windows)
    assert result["Agency A"] == [pytest.approx(3.0, abs=0.001)]
    assert result["Agency B"] == [pytest.approx(0.5, abs=0.001)]


def test_aggregate_excludes_out_of_window_rows():
    df = _make_df([
        ("2025-02-01", "Agency A", 1_000_000, "URG", ""),
        ("2020-06-01", "Agency A", 9_000_000, "URG", ""),  # Biden window, not Trump II
    ])
    windows = _windows_for(["Trump II"])
    result = aggregate_doi_obligations(df, ["Trump II"], windows)
    assert result["Agency A"] == [pytest.approx(1.0, abs=0.001)]


def test_aggregate_rolls_up_small_agencies():
    df = _make_df([
        ("2025-02-01", "Big Agency",  50_000_000, "URG", ""),
        ("2025-02-01", "Tiny Agency",     50_000, "URG", ""),
    ])
    windows = _windows_for(["Trump II"])
    result = aggregate_doi_obligations(df, ["Trump II"], windows)
    assert "Tiny Agency" not in result
    assert "Other DOI bureaus" in result
    assert result["Other DOI bureaus"][0] == pytest.approx(0.05, abs=0.001)


def test_aggregate_trump_ii_is_first_in_sort():
    df = _make_df([
        ("2017-02-01", "Agency A",  5_000_000, "URG", ""),  # Trump I
        ("2025-02-01", "Agency A", 30_000_000, "URG", ""),  # Trump II
        ("2017-02-01", "Agency B", 40_000_000, "URG", ""),  # Trump I only
        ("2025-02-01", "Agency B",  1_000_000, "URG", ""),  # Trump II
    ])
    windows = _windows_for(["Trump I", "Trump II"])
    result = aggregate_doi_obligations(df, ["Trump I", "Trump II"], windows)
    agencies = list(result.keys())
    assert agencies[0] == "Agency A"  # Agency A has higher Trump II ($30M vs $1M)


# ── aggregate_agency_breakdown ───────────────────────────────────────────────

def test_breakdown_splits_by_bucket():
    df = _make_df([
        ("2025-02-01", "Agency A", 2_000_000, "URG", ""),
        ("2025-02-01", "Agency A", 1_000_000, "FOO", ""),
        ("2025-02-01", "Agency A",   500_000, "B",   ""),
    ])
    windows = _windows_for(["Trump II"])
    result = aggregate_agency_breakdown(df, ["Trump II"], windows)
    a = result["Agency A"]
    assert a[JUST_URGENCY]  == [pytest.approx(2.0, abs=0.001)]
    assert a[JUST_FOLLOWON] == [pytest.approx(1.0, abs=0.001)]
    assert a[JUST_OTHER]    == [pytest.approx(0.5, abs=0.001)]


def test_breakdown_produces_all_three_buckets_even_if_zero():
    df = _make_df([
        ("2025-02-01", "Agency A", 2_000_000, "URG", ""),
    ])
    windows = _windows_for(["Trump II"])
    result = aggregate_agency_breakdown(df, ["Trump II"], windows)
    a = result["Agency A"]
    assert JUST_URGENCY  in a
    assert JUST_FOLLOWON in a
    assert JUST_OTHER    in a
```

- [ ] **Step 4.3: Run to confirm they fail**

```bash
pytest tests/test_build_doi_viz.py -v
```

Expected: `ImportError` — `build_doi_viz` module does not exist yet.

- [ ] **Step 4.4: Create build_doi_viz.py**

Create `build_doi_viz.py`:

```python
#!/usr/bin/env python3
"""
Generate doi_viz.html from doi_no_bid_contracts.csv.

Reads doi_no_bid_contracts.csv, applies the same exclusions as compare_admins.py,
aggregates per-agency and per-justification-bucket obligations, and injects the
result into doi_viz_template.html to produce doi_viz.html.

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
)

TRUMP_II_INAUGURATION = TRUMP2_START
EXCLUDE_JUSTIFICATION_CODES = {"OTH", "UT", "ONE", "UNQ"}
OTHER_THRESHOLD_DOLLARS = 100_000

AGENCY_COLORS = {
    "National Park Service":          "#E24B4A",
    "Bureau of Land Management":      "#EF9F27",
    "Bureau of Indian Affairs":       "#4A90D9",
    "U.S. Fish and Wildlife Service": "#5BAD6F",
    "U.S. Geological Survey":         "#9B59B6",
    "Other DOI bureaus":              "#888780",
}
FALLBACK_COLORS = ["#1A7CBF", "#C45E00", "#2E7D32", "#6A1B9A", "#00695C"]

JUST_URGENCY  = "Urgency (FAR 6.302-2)"
JUST_FOLLOWON = "Follow-on contract"
JUST_OTHER    = "Other"
JUST_ORDER    = [JUST_URGENCY, JUST_FOLLOWON, JUST_OTHER]

# Codes in other_than_full_and_open_competition_code that indicate follow-on work.
# Update after inspecting value_counts() on the DOI CSV if new codes appear.
FOLLOW_ON_OTF_CODES      = {"FOO"}
FOLLOW_ON_FAIR_OPP_CODES = {"FOO"}

VIZ_ADMIN_NAMES = ["Trump I", "Biden", "Trump II"]

DOI_VIZ_TEMPLATE = "doi_viz_template.html"
DOI_VIZ_OUTPUT   = "doi_viz.html"
INJECTION_MARKER = "/* __DOI_DATA__ */null/* end */"


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
    return df


def classify_justification(otf: str, fair: str) -> str:
    if otf == "URG" or fair == "URG":
        return JUST_URGENCY
    if otf in FOLLOW_ON_OTF_CODES or fair in FOLLOW_ON_FAIR_OPP_CODES:
        return JUST_FOLLOWON
    return JUST_OTHER


def compute_window(inauguration: date, days: int):
    start = pd.Timestamp(inauguration)
    end = start + pd.Timedelta(days=days - 1)
    return start, end


def aggregate_doi_obligations(
    df: pd.DataFrame, admin_names: list, windows: dict
) -> dict:
    raw = {}
    for agency, grp in df.groupby("awarding_sub_agency_name"):
        vals = []
        for name in admin_names:
            start, end = windows[name]
            mask = (grp["action_date"] >= start) & (grp["action_date"] <= end)
            vals.append(round(float(grp[mask]["federal_action_obligation"].sum()) / 1_000_000, 3))
        raw[agency] = vals

    trump_ii_idx = admin_names.index("Trump II") if "Trump II" in admin_names else 0
    other_vals = [0.0] * len(admin_names)
    to_roll = [
        a for a, vals in raw.items()
        if sum(abs(v) for v in vals) * 1_000_000 < OTHER_THRESHOLD_DOLLARS
    ]
    for a in to_roll:
        for i, v in enumerate(raw.pop(a)):
            other_vals[i] = round(other_vals[i] + v, 3)
    if any(v != 0 for v in other_vals):
        raw["Other DOI bureaus"] = other_vals

    def sort_key(item):
        name, vals = item
        return float("-inf") if name == "Other DOI bureaus" else vals[trump_ii_idx]

    return dict(sorted(raw.items(), key=sort_key, reverse=True))


def aggregate_agency_breakdown(
    df: pd.DataFrame, admin_names: list, windows: dict
) -> dict:
    df = df.copy()
    df["_just"] = df.apply(
        lambda r: classify_justification(
            str(r.get("other_than_full_and_open_competition_code") or ""),
            str(r.get("fair_opportunity_limited_sources_code") or ""),
        ),
        axis=1,
    )
    result = {}
    for agency, grp in df.groupby("awarding_sub_agency_name"):
        buckets = {b: [] for b in JUST_ORDER}
        for name in admin_names:
            start, end = windows[name]
            mask = (grp["action_date"] >= start) & (grp["action_date"] <= end)
            win = grp[mask]
            for bucket in JUST_ORDER:
                val = float(win[win["_just"] == bucket]["federal_action_obligation"].sum())
                buckets[bucket].append(round(val / 1_000_000, 3))
        result[agency] = buckets
    return result


def build_data(df: pd.DataFrame) -> dict:
    today = date.today()
    days_elapsed = (today - TRUMP_II_INAUGURATION).days + 1
    admin_map = {a["name"]: a["inauguration"] for a in ADMINISTRATIONS}
    windows = {name: compute_window(admin_map[name], days_elapsed) for name in VIZ_ADMIN_NAMES}

    doi_obligations = aggregate_doi_obligations(df, VIZ_ADMIN_NAMES, windows)
    all_breakdown   = aggregate_agency_breakdown(df, VIZ_ADMIN_NAMES, windows)

    known_agencies = set(doi_obligations.keys()) - {"Other DOI bureaus"}
    agency_breakdown = {a: all_breakdown[a] for a in known_agencies if a in all_breakdown}

    if "Other DOI bureaus" in doi_obligations:
        other_bd = {b: [0.0] * len(VIZ_ADMIN_NAMES) for b in JUST_ORDER}
        for a, buckets in all_breakdown.items():
            if a not in known_agencies:
                for b in JUST_ORDER:
                    for i, v in enumerate(buckets[b]):
                        other_bd[b][i] = round(other_bd[b][i] + v, 3)
        agency_breakdown["Other DOI bureaus"] = other_bd

    fb_idx = 0
    agency_colors = {}
    for agency in doi_obligations:
        if agency in AGENCY_COLORS:
            agency_colors[agency] = AGENCY_COLORS[agency]
        else:
            agency_colors[agency] = FALLBACK_COLORS[fb_idx % len(FALLBACK_COLORS)]
            fb_idx += 1

    return {
        "days_in_window": days_elapsed,
        "window_label":   f"First {days_elapsed} days",
        "administrations": VIZ_ADMIN_NAMES,
        "agency_colors":   agency_colors,
        "doi_obligations": doi_obligations,
        "agency_breakdown": agency_breakdown,
    }


def inject_and_write(data: dict, template_path: str, output_path: str) -> None:
    with open(template_path, encoding="utf-8") as f:
        html = f.read()
    if INJECTION_MARKER not in html:
        raise ValueError(f"Injection marker '{INJECTION_MARKER}' not found in {template_path}")
    html = html.replace(INJECTION_MARKER, json.dumps(data, ensure_ascii=False))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    df = load_contracts(DOI_OUTPUT_CSV)
    print(f"Loaded {len(df):,} DOI transactions, {df['contract_award_unique_key'].nunique():,} unique awards")
    data = build_data(df)

    agencies = list(data["doi_obligations"].keys())
    print(f"Agencies in viz ({len(agencies)}): {agencies}")
    for name in VIZ_ADMIN_NAMES:
        idx = VIZ_ADMIN_NAMES.index(name)
        total = sum(v[idx] for v in data["doi_obligations"].values())
        print(f"  {name}: ${total:.1f}M total")

    inject_and_write(data, DOI_VIZ_TEMPLATE, DOI_VIZ_OUTPUT)
    print(f"\nWrote {DOI_VIZ_OUTPUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4.5: Run the new tests**

```bash
pytest tests/test_build_doi_viz.py -v
```

Expected: all pass.

- [ ] **Step 4.6: Run the full test suite**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 4.7: Commit source files**

```bash
git add build_doi_viz.py tests/test_build_doi_viz.py
git commit -m "Add build_doi_viz.py with aggregation and template injection logic"
```

---

## Task 5: End-to-end run and commit generated output

- [ ] **Step 5.1: Run fetch_contracts.py**

```bash
source .venv/bin/activate
python fetch_contracts.py
```

This will re-download all years under the new `doi_contracts_YYYY.zip` naming (old `nps_contracts_YYYY.zip` are ignored). Expect ~20–30 minutes. Verify the final output:

```
Wrote N transactions → doi_no_bid_contracts.csv
Derived NPS subset: M transactions → nps_no_bid_contracts.csv
```

Check M (NPS subset) is close to the prior row count (~28,988) — exact match not expected since we now cover more years via DOI toptier which may catch previously-missed NPS transactions.

- [ ] **Step 5.2: Re-run compare_admins.py to confirm it still works**

```bash
python compare_admins.py
```

Expected: same output format as before, reading from `nps_no_bid_contracts.csv`.

- [ ] **Step 5.3: Inspect DOI follow-on codes and update FOLLOW_ON_OTF_CODES if needed**

```bash
python -c "
import pandas as pd
df = pd.read_csv('doi_no_bid_contracts.csv', dtype=str)
excl = {'OTH', 'UT', 'ONE', 'UNQ'}
df = df[~df['other_than_full_and_open_competition_code'].isin(excl)]
df = df[df['fair_opportunity_limited_sources_code'].fillna('') != 'FAIR']
print('=== other_than_full_and_open_competition_code (non-excluded) ===')
print(df['other_than_full_and_open_competition_code'].value_counts().head(20))
print()
print('=== fair_opportunity_limited_sources_code ===')
print(df['fair_opportunity_limited_sources_code'].value_counts().head(20))
"
```

If codes other than `FOO` appear that clearly indicate follow-on work, add them to `FOLLOW_ON_OTF_CODES` or `FOLLOW_ON_FAIR_OPP_CODES` in `build_doi_viz.py`.

- [ ] **Step 5.4: Run build_doi_viz.py**

```bash
python build_doi_viz.py
```

Expected output (values will be real):
```
Loaded N,NNN DOI transactions, N,NNN unique awards
Agencies in viz (6): ['Bureau of Land Management', 'National Park Service', ...]
  Trump I: $XXX.XM total
  Biden: $XXX.XM total
  Trump II: $XXX.XM total

Wrote doi_viz.html
```

- [ ] **Step 5.5: Open doi_viz.html in a browser and verify**

Open `doi_viz.html` directly in a browser (file://) and check:

1. "All DOI" default view shows stacked bars with one segment per bureau, Trump II tallest
2. Dropdown lists all agencies; selecting one swaps to Urgency/Follow-on/Other stacked bars
3. Legend swaps between agency names and justification names on dropdown change
4. Title and subtitle update when an agency is selected
5. Hover tooltip shows per-segment values and total footer
6. Selecting NPS and comparing to existing `viz.html` — numbers should be in the same ballpark (not necessarily identical since `build_doi_viz.py` uses total obligations not new-award-only, but the relative proportions should match)

- [ ] **Step 5.6: Commit final outputs**

```bash
git add doi_viz.html nps_no_bid_contracts.csv doi_no_bid_contracts.csv
git commit -m "Add doi_viz.html and updated CSVs from DOI-wide fetch"
```

---

## Self-Review Checklist

- **spec coverage:** config rename ✓, Obama entries ✓, DOI fetch ✓, NPS derivation ✓, ZIP rename ✓, template ✓, build script ✓, agency dropdown ✓, dual chart state ✓, justification buckets ✓, doi_viz.html committed ✓, existing scripts unchanged ✓
- **no placeholders:** all steps contain complete code; follow-on code determination is an explicit data-exploration step, not a TBD
- **type consistency:** `aggregate_doi_obligations` returns `dict[str, list[float]]`; `aggregate_agency_breakdown` returns `dict[str, dict[str, list[float]]]`; both consumed correctly in `build_data`; `inject_and_write` signature matches calls in `main` and tests
