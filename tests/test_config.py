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
