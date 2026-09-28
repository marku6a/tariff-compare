from ingestion.raw_schema import RAW_SCHEMA_HEADERS

EXPECTED_RAW_SCHEMA_HEADERS = (
    "meter_id",
    "interval_timestamp",
    "energy_value",
    "source_fields",
)


def test_raw_schema():
    assert RAW_SCHEMA_HEADERS == EXPECTED_RAW_SCHEMA_HEADERS
