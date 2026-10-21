import csv
from pathlib import Path

from ingestion.raw_schema import METER_READINGS_RAW_HEADERS, TARIFF_RAW_HEADERS

EXPECTED_METER_READINGS_RAW_HEADERS = (
    "meter_id",
    "interval_timestamp",
    "energy_value",
    "source_fields",
)

EXPECTED_TARIFF_RAW_HEADERS = (
    "tariff_id",
    "tariff_name",
    "supplier",
    "fix_length_months",
    "exit_fee_pounds",
    "standing_charge_pence_per_day",
    "day_type",
    "start_time_local",
    "end_time_local",
    "unit_rate_pence_per_kwh",
)


def test_meter_readings_raw_schema():
    assert METER_READINGS_RAW_HEADERS == EXPECTED_METER_READINGS_RAW_HEADERS


def test_tariff_raw_schema():
    assert TARIFF_RAW_HEADERS == EXPECTED_TARIFF_RAW_HEADERS


def test_tariff_raw_schema_matches_csv_template():
    template = (
        Path(__file__).resolve().parents[1] / "data/templates/tariffs_template.csv"
    )
    with template.open(newline="", encoding="utf-8") as source:
        assert tuple(next(csv.reader(source))) == TARIFF_RAW_HEADERS
