"""Shared validation and failure-safe output helpers for data generators."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class GeneratorError(ValueError):
    """Report a deterministic source-data or generation failure."""


def require(condition: bool, message: str) -> None:
    """Raise an actionable generator error when a requirement is false."""

    if not condition:
        raise GeneratorError(message)


def write_or_check(output_path: Path, generated: str, check: bool) -> None:
    """Check output or atomically replace it after a verified temporary write."""

    if check:
        try:
            existing = output_path.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise GeneratorError(f"Generated library does not exist: {output_path}") from error
        require(existing == generated, f"Generated library is stale: {output_path}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(generated)
            stream.flush()
            os.fsync(stream.fileno())
        require(
            temporary_path.read_text(encoding="utf-8") == generated,
            f"Temporary generated library failed verification: {temporary_path}",
        )
        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
