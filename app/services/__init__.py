"""Service layer helpers."""
from dataclasses import dataclass


@dataclass(slots=True)
class ImportedScript:
    """Simple representation of a script imported from an external provider."""

    title: str
    content: str
