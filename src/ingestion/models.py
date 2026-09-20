from pathlib import Path
from typing import Literal
from collections.abc import Mapping
from dataclasses import dataclass

SourceKind = Literal["meter_readings", "tariff"]
RawValue = str | None
RawRow = Mapping[str, RawValue]

@dataclass(frozen=True, slots=True)
class RawBatch:
    # A source file read without interpretation

    provider: str
    source_kind: SourceKind
    source_path: Path
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
                    f"Row is {row_number} does not match headers. "
                    f"Missing: {sorted(missing)}. "
                    f"Unexpected: {sorted(unexpected)}."
                )