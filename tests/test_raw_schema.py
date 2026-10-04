from ingestion.raw_schema import METER_READINGS_RAW_HEADERS

EXPECTED_METER_READINGS_RAW_HEADERS = (
    "meter_id",
    "interval_timestamp",
    "energy_value",
    "source_fields",
)


def test_meter_readings_raw_schema():
    assert METER_READINGS_RAW_HEADERS == EXPECTED_METER_READINGS_RAW_HEADERS
