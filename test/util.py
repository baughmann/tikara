import shutil
import zipfile
from pathlib import Path


def extract_and_cleanup_zip(zip_path: Path, extra_files_to_delete: list[str] | None = None) -> None:
    """
    Extract zip contents to parent directory and delete the zip file.

    Args:
        zip_path: Path to the zip file
    """
    # Get the parent directory
    parent_dir = zip_path.parent

    # Extract all contents to a temporary directory
    temp_extract_dir = parent_dir / "temp_extract"
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_extract_dir)

    # Move all contents to parent directory
    for item in temp_extract_dir.iterdir():
        # Construct destination path
        dest = parent_dir / item.name
        # Move the item
        shutil.move(str(item), str(dest))

    # Clean up
    temp_extract_dir.rmdir()  # Remove temporary directory
    zip_path.unlink()  # Delete the zip file

    # Delete extra files
    if extra_files_to_delete:
        for file in extra_files_to_delete:
            (parent_dir / file).unlink()
