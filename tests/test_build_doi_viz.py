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
