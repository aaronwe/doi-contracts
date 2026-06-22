import pandas as pd
import pytest

from analyze_urgency import build_links_cell, generate_report, ja_status, truncate


# ── Helpers ───────────────────────────────────────────────────────────────────

def test_truncate_short_string_unchanged():
    assert truncate("hello world", 120) == "hello world"


def test_truncate_long_string_gets_ellipsis():
    long = "x" * 130
    result = truncate(long, 120)
    assert result.endswith("…")
    assert len(result) == 121  # 120 chars + ellipsis character


def test_truncate_handles_none():
    assert truncate(None, 120) == ""


def test_ja_status_downloaded():
    row = pd.Series({"doc_local_path": "docs/justifications/PIID1/doc.pdf", "doc_url": ""})
    assert ja_status(row) == "Downloaded"


def test_ja_status_link_only_with_doc_url():
    row = pd.Series({"doc_local_path": "", "doc_url": "https://example.com/doc.pdf"})
    assert ja_status(row) == "Link only"


def test_ja_status_link_only_no_doc():
    row = pd.Series({"doc_local_path": "", "doc_url": ""})
    assert ja_status(row) == "Link only"


def test_build_links_cell_includes_both_links():
    row = pd.Series({
        "usaspending_url": "https://usaspending.gov/award/AWD1/",
        "sam_piid_url": "https://sam.gov/search/?keywords=PIID1&index=co",
        "sam_solicitation_url": "https://sam.gov/search/?keywords=SOL1&index=opp",
    })
    cell = build_links_cell(row)
    assert "[USASpending]" in cell
    assert "[SAM (PIID)]" in cell
    assert "[SAM (Solicitation)]" in cell


def test_build_links_cell_skips_empty_solicitation():
    row = pd.Series({
        "usaspending_url": "https://usaspending.gov/award/AWD1/",
        "sam_piid_url": "https://sam.gov/search/?keywords=PIID1&index=co",
        "sam_solicitation_url": "",
    })
    cell = build_links_cell(row)
    assert "[SAM (Solicitation)]" not in cell


# ── Report generation ─────────────────────────────────────────────────────────

def _make_awards():
    return pd.DataFrame({
        "contract_award_unique_key": ["AWD1", "AWD2"],
        "award_id_piid": ["PIID1", "PIID2"],
        "recipient_name": ["Big Corp LLC", "Small Biz Inc"],
        "prime_award_base_transaction_description": [
            "URGENT RENOVATION OF REFLECTING POOL",
            "EMERGENCY HVAC REPAIR",
        ],
        "total_obligation": [1_500_000.0, 50_000.0],
        "first_action_date": ["2025-06-01", "2025-03-01"],
        "product_or_service_code_description": ["Construction", "HVAC Repair"],
        "primary_place_of_performance_city_name": ["Washington", "New York"],
        "primary_place_of_performance_state_code": ["DC", "NY"],
    })


def _make_manifest():
    return pd.DataFrame({
        "award_id_piid": ["PIID1", "PIID2"],
        "usaspending_url": [
            "https://www.usaspending.gov/award/AWD1/",
            "https://www.usaspending.gov/award/AWD2/",
        ],
        "sam_piid_url": [
            "https://sam.gov/search/?keywords=PIID1&index=co",
            "https://sam.gov/search/?keywords=PIID2&index=co",
        ],
        "sam_solicitation_url": [
            "https://sam.gov/search/?keywords=SOL1&index=opp",
            "",
        ],
        "doc_url": ["https://example.com/ja.pdf", ""],
        "doc_local_path": ["docs/justifications/PIID1/ja.pdf", ""],
    })


def test_generate_report_contains_header_block():
    report = generate_report(_make_awards(), _make_manifest())
    assert "# NPS Urgency Contract Investigation" in report
    assert "2025-01-20" in report
    assert "2" in report


def test_generate_report_sorts_by_obligation_descending():
    report = generate_report(_make_awards(), _make_manifest())
    assert report.index("PIID1") < report.index("PIID2")


def test_generate_report_formats_dollars():
    report = generate_report(_make_awards(), _make_manifest())
    assert "$1,500,000" in report
    assert "$50,000" in report


def test_generate_report_shows_downloaded_status():
    report = generate_report(_make_awards(), _make_manifest())
    assert "Downloaded" in report


def test_generate_report_shows_link_only_status():
    report = generate_report(_make_awards(), _make_manifest())
    assert "Link only" in report


def test_generate_report_works_without_manifest(tmp_path):
    """analyze_urgency.py should still produce a report if manifest is missing."""
    empty_manifest = pd.DataFrame(columns=[
        "award_id_piid", "usaspending_url", "sam_piid_url",
        "sam_solicitation_url", "doc_url", "doc_local_path",
    ])
    report = generate_report(_make_awards(), empty_manifest)
    assert "PIID1" in report
    assert "PIID2" in report
