from ingestion.models import RawBatch


def validate_batch(batch: RawBatch) -> None:
    # at least one row
    if not batch.rows:
        raise ValueError("Batch must contain at least one row")

    # no structurally missing values
    for row_index, row in enumerate(batch.rows, start=1):

        missing_values = sorted(
            header for header, value in row.items() if value is None
        )

        if missing_values:
            raise ValueError(
                f"Row {row_index} has structurally missing values for: "
                f"{', '.join(missing_values)}."
            )
