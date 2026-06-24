import json
from pathlib import Path
from typing import Optional


def validate_samples_for_dialect(samples: list, dialect: str) -> Optional[str]:
    """Return an error message if any sample is invalid for the given dialect, else None."""
    key = f"ch_{dialect.lower()}"
    for i, item in enumerate(samples):
        if not isinstance(item, dict):
            return f'Item {i} must be a JSON object (got {type(item).__name__}).'
        if "id" not in item or "de" not in item:
            return f'Item {i} must include "id" and "de".'
        if "ch" not in item and key not in item:
            return f'Item {i} must include "ch" or "{key}".'
    return None


def read_dataset(path: Path, dialect_filter: Optional[str] = None) -> list[dict]:
    """
    Reads a JSON dataset from the given path and validates its structure.
    Expected format:
        [
            {"id": "string", "de": "string"},
            ...
        ]
    """
    with open(path, mode="r", encoding="utf-8") as f:
        data = json.load(f)

    # Check that the top-level element is a list
    if not isinstance(data, list):
        return []

    if dialect_filter:
        filtered_data = [sample for sample in data if f"ch_{dialect_filter}" in sample]
    else:
        filtered_data = data

    # Validate each item in the list
    for i, item in enumerate(filtered_data):
        if not isinstance(item, dict):
            return []
        if "id" not in item or "de" not in item:
            return []

    return filtered_data
