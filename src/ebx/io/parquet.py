"""Parquet writing and round-trip facade."""

from src.ingestion.loader import require_pyarrow, write_parquet

__all__ = ["require_pyarrow", "write_parquet"]
