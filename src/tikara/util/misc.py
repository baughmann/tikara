"""Miscellaneous utility functions."""

from pathlib import Path
from typing import TYPE_CHECKING

from tikara.error_handling import TikaInputFileNotFoundError

if TYPE_CHECKING:
    from tikara.data_types import TikaParseOutputFormat


def _validate_and_prepare_output_file(
    output_file: Path | str | None,
    output_format: "TikaParseOutputFormat",
) -> Path | None:
    if output_file:
        if isinstance(output_file, str):
            output_file = Path(output_file)
        if not output_file.parent.exists():
            output_file.parent.mkdir(parents=True)
        if output_file.suffix:
            output_file = output_file.with_suffix(f".{output_format}")
        return output_file

    return None


def _validate_input_file(input_file: Path | str) -> Path:
    if isinstance(input_file, str):
        input_file = Path(input_file)
    if not input_file.exists():
        raise TikaInputFileNotFoundError._from_file(input_file)
    return input_file
