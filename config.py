from datetime import date

NPS_SUBTIER_NAME = "National Park Service"
DOI_TOPTIER_NAME = "Department of the Interior"
NPS_SUBTIER_CODE = "1443"  # Confirmed from FPDS subtier in contract URLs

# FPDS extent_competed codes for other-than-full-and-open competition
# B = Not Available for Competition (sole source under FAR 6.302 exceptions)
# C = Not Competed (includes urgency FAR 6.302-2, sole source, etc.)
NO_BID_CODES = {"B", "C"}

# fair_opportunity_limited_sources_code values indicating non-competitive IDV task orders.
# These orders inherit a competed parent's extent_competed_code (A/D), so they would be
# filtered out by NO_BID_CODES alone. Capturing them fixes the GSA Schedule blindspot.
# FAIR = Fair Opportunity Given (competed — exclude from no-bid analysis)
IDV_SOLE_SOURCE_FAIR_OPP_CODES = {"URG"}
# Excluded from IDV scope:
#   ONE = Only One Source — typically proprietary software/equipment with a single
#         manufacturer (Taser, ESRI, Adobe). Not a discretionary competition bypass.
#   SS  = Sole Source — same pattern; directed orders to incumbents with unique
#         site-specific knowledge. Routine procurement mechanics, not policy choices.
#   FOO = Follow-On Action Following Competitive Initial Action — continuation of
#         competed work, not a competition bypass
#   OSA = Other Statutory Authority — equivalent to OTH (8(a)/ANC set-asides via IDV)

# USASpending contract award type codes (A=BPA, B=Purchase Order, C=Delivery Order, D=Definitive Contract)
CONTRACT_AWARD_TYPES = ["A", "B", "C", "D"]

API_BASE = "https://api.usaspending.gov/api/v2"

# Five administrations: inauguration date defines start of comparison window.
# Comparison window = [inauguration, inauguration + days_trump_ii_in_office] for each.
ADMINISTRATIONS = [
    {"name": "Trump II",  "inauguration": date(2025, 1, 20)},
    {"name": "Biden",     "inauguration": date(2021, 1, 20)},
    {"name": "Trump I",   "inauguration": date(2017, 1, 20)},
    {"name": "Obama II",  "inauguration": date(2013, 1, 20)},
    {"name": "Obama I",   "inauguration": date(2009, 1, 20)},
]

# Earliest date to pull data (Obama I inauguration)
DATA_START_DATE = date(2009, 1, 20)

DOI_OUTPUT_CSV = "doi_no_bid_contracts.csv"
NPS_OUTPUT_CSV = "nps_no_bid_contracts.csv"
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
    "fair_opportunity_limited_sources_code",
    "fair_opportunity_limited_sources",
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
TRUMP2_START = ADMINISTRATIONS[0]["inauguration"]
URG_CODE = "URG"  # other_than_full_and_open_competition_code value for FAR 6.302-2 urgency
MANIFEST_CSV = "justifications_manifest.csv"
JUSTIFICATIONS_DIR = "docs/justifications"
INVESTIGATION_MD = "urgency_investigation.md"
