import csv
import os
import pandas as pd
import pytest
import requests_mock as rm

from fetch_justifications import (
    MANIFEST_FIELDS,
    append_manifest_row,
    load_manifest,
    make_fpds_search_url,
    make_sam_solicitation_url,
    make_usaspending_url,
)


# ── URL builders ──────────────────────────────────────────────────────────────

def test_make_usaspending_url():
    key = "CONT_AWD_140P2026C0028_1443_-NONE-_-NONE-"
    assert make_usaspending_url(key) == f"https://www.usaspending.gov/award/{key}/"


def test_make_fpds_search_url_contains_piid():
    url = make_fpds_search_url("140P2026C0028")
    assert "140P2026C0028" in url
    assert "sam.gov" in url or "fpds.gov" in url


def test_make_sam_solicitation_url_with_identifier():
    url = make_sam_solicitation_url("140P2026R0050")
    assert "140P2026R0050" in url
    assert "sam.gov" in url


def test_make_sam_solicitation_url_with_empty_identifier():
    assert make_sam_solicitation_url("") == ""
    assert make_sam_solicitation_url(None) == ""


# ── Manifest I/O ──────────────────────────────────────────────────────────────

def _empty_row(piid: str) -> dict:
    return {k: ("" if k != "award_id_piid" else piid) for k in MANIFEST_FIELDS}


def test_load_manifest_returns_empty_set_when_no_file(tmp_path):
    assert load_manifest(str(tmp_path / "nonexistent.csv")) == set()


def test_append_manifest_row_creates_file_with_header(tmp_path):
    path = str(tmp_path / "manifest.csv")
    append_manifest_row(path, _empty_row("PIID1"))

    df = pd.read_csv(path, dtype=str)
    assert list(df.columns) == MANIFEST_FIELDS
    assert len(df) == 1
    assert df.iloc[0]["award_id_piid"] == "PIID1"


def test_append_manifest_row_does_not_duplicate_header(tmp_path):
    path = str(tmp_path / "manifest.csv")
    append_manifest_row(path, _empty_row("PIID1"))
    append_manifest_row(path, _empty_row("PIID2"))

    df = pd.read_csv(path, dtype=str)
    assert len(df) == 2
    assert list(df.columns) == MANIFEST_FIELDS


def test_load_manifest_returns_set_of_piids(tmp_path):
    path = str(tmp_path / "manifest.csv")
    for piid in ["PIID1", "PIID2", "PIID3"]:
        append_manifest_row(path, _empty_row(piid))

    result = load_manifest(path)
    assert result == {"PIID1", "PIID2", "PIID3"}
