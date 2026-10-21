from pathlib import Path
from typing import Literal
from typing import get_args
from collections.abc import Mapping
from dataclasses import dataclass

SourceKind = Literal["meter_readings", "tariff"]
TimestampBoundary = Literal["start", "end"]
EnergyUnit = Literal["wh", "kwh"]
RawValue = str | None
RawRow = Mapping[str, RawValue]


@dataclass(frozen=True, slots=True)
class MeterReadingMetadata:
    timestamp_boundary: TimestampBoundary
    timestamp_timezone: str
    energy_unit: EnergyUnit
    interval_duration_minutes: int

    def __post_init__(self) -> None:
        if self.timestamp_boundary not in get_args(TimestampBoundary):
            raise ValueError("Invalid timestamp boundary")

        if self.energy_unit not in get_args(EnergyUnit):
            raise ValueError("Invalid energy unit")

        if (
            not isinstance(self.timestamp_timezone, str)
            or not self.timestamp_timezone.strip()
        ):
            raise ValueError("Meter readings should have a nonblank timezone")

        if (
            not isinstance(self.interval_duration_minutes, int)
            or isinstance(self.interval_duration_minutes, bool)
            or self.interval_duration_minutes <= 0
        ):
            raise ValueError("Meter readings should have a positive interval duration")


@dataclass(frozen=True, slots=True)
class RawBatch:
    # Source values mapped to headers and rows as strings.
    # The rest of the slots are populated by an adapter.

    source_format: str
    source_kind: SourceKind
    source_path: Path
    headers: tuple[str, ...]
    rows: tuple[RawRow, ...]
    meter_metadata: MeterReadingMetadata | None = None

    def __post_init__(self) -> None:
        self._validate_source_kind()
        self._validate_row_structure()
        self._validate_metadata()

    def _validate_source_kind(self) -> None:
        if self.source_kind not in get_args(SourceKind):
            raise ValueError("Invalid source kind")

    def _validate_row_structure(self) -> None:
        if len(self.headers) != len(set(self.headers)):
            raise ValueError("Headers must be unique.")

        expected_keys = set(self.headers)

        for row_number, row in enumerate(self.rows, start=1):
            actual_keys = set(row)

            if actual_keys != expected_keys:
                missing = expected_keys - actual_keys
                unexpected = actual_keys - expected_keys

                raise ValueError(
                    f"Row {row_number} does not match headers. "
                    f"Missing: {sorted(missing)}. "
                    f"Unexpected: {sorted(unexpected)}."
                )

    def _validate_metadata(self) -> None:
        if self.source_kind == "meter_readings":
            if not isinstance(self.meter_metadata, MeterReadingMetadata):
                raise ValueError("Meter readings require MeterReadingMetadata")
        elif self.meter_metadata is not None:
            raise ValueError("Tariff should not have meter metadata")
