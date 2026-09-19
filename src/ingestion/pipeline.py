"""Orchestrate source selection, raw loading, and ingestion metadata."""

# This module will select a provider adapter, retain the source identity, and
# pass source-level values to the raw loader. It must not cast or apply data
# quality and business rules; those belong to dbt.
