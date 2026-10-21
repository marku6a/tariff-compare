"""Stable source-level column names for meter readings and tariffs."""

METER_READINGS_RAW_HEADERS = (
    "meter_id",
    "interval_timestamp",
    "energy_value",
    "source_fields",
)

TARIFF_RAW_HEADERS = (
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
