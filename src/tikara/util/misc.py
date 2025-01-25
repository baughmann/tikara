from pathlib import Path

from tikara.util.tika import TikaParseOutputFormat


def _validate_and_prepare_output_file(
    output_file: Path | str | None,
    output_format: TikaParseOutputFormat,
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
