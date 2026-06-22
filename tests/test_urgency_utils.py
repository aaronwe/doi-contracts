def test_config_has_required_constants():
    import config
    from datetime import date

    assert config.TRUMP2_START == date(2025, 1, 20)
    assert config.URG_CODE == "URG"
    assert config.MANIFEST_CSV == "justifications_manifest.csv"
    assert config.JUSTIFICATIONS_DIR == "docs/justifications"
    assert config.INVESTIGATION_MD == "urgency_investigation.md"
    assert config.TRUMP2_START == config.ADMINISTRATIONS[0]["inauguration"]
