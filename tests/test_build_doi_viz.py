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
    # amount is in $M (1_000_000 + 500_000 - 100_000 = 1_400_000 → 1.4)
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
        ("2025-03-01", "AWD-2", "P002", "Bureau of Land Management", 500_000, "NV", "V", "D"),
    ])
    windows = _windows_for(["Trump II"])
    result = build_contracts_table(df, ["Trump II"], windows)
    by_piid = {r["piid"]: r for r in result}
    assert by_piid["P001"]["agency_short"] == "NPS"
    assert by_piid["P001"]["agency"] == "National Park Service"
    assert by_piid["P002"]["agency_short"] == "BLM"
    assert by_piid["P002"]["agency"] == "Bureau of Land Management"


def test_contracts_table_usaspending_url_contains_award_key():
    df = _make_full_df([
        ("2025-02-01", "CONT_AWD_140P2026C0028_1443_-NONE-_-NONE-", "P001",
         "National Park Service", 1_000_000, "DC", "V", "D"),
    ])
    windows = _windows_for(["Trump II"])
    result = build_contracts_table(df, ["Trump II"], windows)
    assert "CONT_AWD_140P2026C0028_1443_-NONE-_-NONE-" in result[0]["url"]
    assert result[0]["url"].startswith("https://www.usaspending.gov/award/")
