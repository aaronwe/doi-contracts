import importlib


def test_config_has_required_constants():
    import config
    from datetime import date

    assert hasattr(config, "TRUMP2_START")
    assert isinstance(config.TRUMP2_START, date)
    assert config.TRUMP2_START.year == 2025

    assert hasattr(config, "URG_CODE")
    assert config.URG_CODE == "URG"

    assert hasattr(config, "MANIFEST_CSV")
    assert config.MANIFEST_CSV.endswith(".csv")

    assert hasattr(config, "JUSTIFICATIONS_DIR")
    assert "justifications" in config.JUSTIFICATIONS_DIR

    assert hasattr(config, "INVESTIGATION_MD")
    assert config.INVESTIGATION_MD.endswith(".md")
