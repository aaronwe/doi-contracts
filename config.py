from datetime import date

NPS_SUBTIER_NAME = "National Park Service"
DOI_TOPTIER_NAME = "Department of the Interior"
NPS_SUBTIER_CODE = "1443"  # Confirmed from FPDS subtier in contract URLs

# FPDS extent_competed codes for other-than-full-and-open competition
# B = Not Available for Competition (sole source under FAR 6.302 exceptions)
# C = Not Competed (includes urgency FAR 6.302-2, sole source, etc.)
NO_BID_CODES = {"B", "C"}

# USASpending contract award type codes (A=BPA, B=Purchase Order, C=Delivery Order, D=Definitive Contract)
CONTRACT_AWARD_TYPES = ["A", "B", "C", "D"]

API_BASE = "https://api.usaspending.gov/api/v2"

# Four administrations: inauguration date defines start of comparison window.
# Comparison window = [inauguration, inauguration + days_trump_ii_in_office] for each.
ADMINISTRATIONS = [
    {"name": "Trump II",  "inauguration": date(2025, 1, 20)},
    {"name": "Biden",     "inauguration": date(2021, 1, 20)},
    {"name": "Trump I",   "inauguration": date(2017, 1, 20)},
]

# Earliest date to pull data (Obama I inauguration)
DATA_START_DATE = date(2009, 1, 20)

OUTPUT_CSV = "nps_no_bid_contracts.csv"
COMPARISON_CSV = "admin_comparison.csv"
DOWNLOADS_DIR = "downloads"

# Columns to keep from the raw bulk download CSV
KEEP_COLUMNS = [
    "contract_transaction_unique_key",
    "contract_award_unique_key",
    "award_id_piid",
    "action_date",
    "period_of_performance_start_date",
    "period_of_performance_current_end_date",
    "federal_action_obligation",
    "recipient_name",
    "recipient_uei",
    "awarding_sub_agency_code",
    "awarding_sub_agency_name",
    "prime_award_base_transaction_description",
    "transaction_description",
    "extent_competed_code",
    "extent_competed",
    "solicitation_procedures_code",
    "solicitation_procedures",
    "other_than_full_and_open_competition_code",
    "other_than_full_and_open_competition",
    "naics_code",
    "naics_description",
    "product_or_service_code",
    "product_or_service_code_description",
    "primary_place_of_performance_city_name",
    "primary_place_of_performance_state_code",
    "primary_place_of_performance_state_name",
]

# Urgency investigation tool
TRUMP2_START = date(2025, 1, 20)
URG_CODE = "URG"
MANIFEST_CSV = "justifications_manifest.csv"
JUSTIFICATIONS_DIR = "docs/justifications"
INVESTIGATION_MD = "urgency_investigation.md"
