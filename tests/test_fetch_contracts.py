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
