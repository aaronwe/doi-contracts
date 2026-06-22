def test_config_has_required_constants():
    import config
    from datetime import date

    assert config.TRUMP2_START == date(2025, 1, 20)
    assert config.URG_CODE == "URG"
    assert config.MANIFEST_CSV == "justifications_manifest.csv"
    assert config.JUSTIFICATIONS_DIR == "docs/justifications"
    assert config.INVESTIGATION_MD == "urgency_investigation.md"
    assert config.TRUMP2_START == config.ADMINISTRATIONS[0]["inauguration"]


import pandas as pd
import pytest
from urgency_utils import load_trump2_urg_awards


def _make_csv(tmp_path, rows):
    """Write a minimal contracts CSV for testing."""
    cols = [
        "contract_transaction_unique_key",
        "contract_award_unique_key",
        "award_id_piid",
        "action_date",
        "federal_action_obligation",
        "other_than_full_and_open_competition_code",
        "recipient_name",
        "prime_award_base_transaction_description",
        "product_or_service_code_description",
        "primary_place_of_performance_city_name",
        "primary_place_of_performance_state_code",
    ]
    df = pd.DataFrame(rows, columns=cols)
    path = str(tmp_path / "contracts.csv")
    df.to_csv(path, index=False)
    return path


def test_load_filters_to_trump2_urg(tmp_path):
    """Only awards in Trump II (>=2025-01-20) with URG code are returned."""
    rows = [
        ["TXN1", "AWD1", "PIID1", "2025-06-01", "100000.00", "URG", "Vendor A", "Urgent work", "Construction", "DC", "DC"],
        ["TXN2", "AWD1", "PIID1", "2025-07-01", "50000.00",  "URG", "Vendor A", "Urgent work", "Construction", "DC", "DC"],
        ["TXN3", "AWD2", "PIID2", "2025-03-01", "200000.00", "B",   "Vendor B", "No-bid work",  "HVAC",         "NY", "NY"],
        ["TXN4", "AWD3", "PIID3", "2024-12-01", "999000.00", "URG", "Vendor C", "Earlier work", "Plumbing",     "LA", "CA"],
        ["TXN5", "AWD4", "PIID4", "2025-04-01", "75000.00",  "URG", "Vendor D", "Urgent too",   "Painting",     "TX", "TX"],
    ]
    path = _make_csv(tmp_path, rows)
    result = load_trump2_urg_awards(path)

    assert len(result) == 2
    assert set(result["award_id_piid"]) == {"PIID1", "PIID4"}


def test_load_sums_obligations_per_award(tmp_path):
    """Obligations are summed across all transactions for an award."""
    rows = [
        ["TXN1", "AWD1", "PIID1", "2025-06-01", "100000.00", "URG", "Vendor A", "Work A", "PSC", "DC", "DC"],
        ["TXN2", "AWD1", "PIID1", "2025-07-01",  "50000.00", "URG", "Vendor A", "Work A", "PSC", "DC", "DC"],
        ["TXN3", "AWD1", "PIID1", "2025-08-01",  "-10000.00","URG", "Vendor A", "Work A", "PSC", "DC", "DC"],
    ]
    path = _make_csv(tmp_path, rows)
    result = load_trump2_urg_awards(path)

    assert len(result) == 1
    assert abs(result.iloc[0]["total_obligation"] - 140000.0) < 0.01


def test_load_returns_first_action_date(tmp_path):
    """first_action_date reflects the earliest transaction for each award."""
    rows = [
        ["TXN1", "AWD1", "PIID1", "2025-07-01", "50000.00", "URG", "V", "D", "P", "C", "DC"],
        ["TXN2", "AWD1", "PIID1", "2025-06-01", "50000.00", "URG", "V", "D", "P", "C", "DC"],
    ]
    path = _make_csv(tmp_path, rows)
    result = load_trump2_urg_awards(path)

    assert result.iloc[0]["first_action_date"] == "2025-06-01"
