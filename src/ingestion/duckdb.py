"""Write append-only source landing tables and ingestion metadata to DuckDB."""

# The raw store is Python's only write target. Analytics consumers attach it
# read-only through dbt.
