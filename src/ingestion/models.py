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
class RawBatch:
    # Source values mapped to headers and rows as strings.
    # The rest of the slots are populated by an adapter.

    provider: str
    source_kind: SourceKind
    source_path: Path
    timestamp_boundary: TimestampBoundary | None
    timestamp_timezone: str | None
    energy_unit: EnergyUnit | None
    interval_duration_minutes: int | None
    headers: tuple[str, ...]
    rows: tuple[RawRow, ...]

    def __post_init__(self) -> None:
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
        if self.source_kind not in get_args(SourceKind):
            raise ValueError("Invalid source kind")

        if self.source_kind == "meter_readings":
            # meter_readings checks
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
                raise ValueError(
                    "Meter readings should have a positive interval duration"
                )

        if self.source_kind == "tariff":
            # tariff checks
            if self.timestamp_boundary is not None:
                raise ValueError("Tariff should not have timestamp boundary")

            if self.energy_unit is not None:
                raise ValueError("Tariff should not have energy unit")

            if self.timestamp_timezone is not None:
                raise ValueError("Tariff should not have timezone")

            if self.interval_duration_minutes is not None:
                raise ValueError("Tariff should not have interval duration")
