import os
import tempfile
from pathlib import Path

import pytest
import requests
from testcontainers.core.container import DockerContainer

from test.util import extract_and_cleanup_zip
from tikara.core import Tika

UNPACK_RECURSIVE_TEST_CASES: list[tuple[str, list[str], int]] = [
    ("test_recursive_embedded_docx", ["embed1.zip", "image1.emf"], 1),
    ("test_recursive_embedded_docx", ["embed1.zip", "image1.emf", "embed1/embed1a.txt"], 2),
    ("demo_docx", ["image2.png", "image3.png", "image4.png"], 1),
    ("demo_docx", ["image2.png", "image3.png", "image4.png"], 2),
    ("basic_txt", [], 1),
    ("basic_txt", [], 2),
]


@pytest.mark.parametrize(("fixture_name", "expected_embedded_file_names", "max_depth"), UNPACK_RECURSIVE_TEST_CASES)
def test_unpack_docx_with_embedded_files(
    tika: Tika,
    request: pytest.FixtureRequest,
    fixture_name: str,
    expected_embedded_file_names: list[str],
    max_depth: int,
) -> None:
    """Test unpacking a Word document containing embedded files."""
    input_file_path: Path = request.getfixturevalue(fixture_name)

    with tempfile.TemporaryDirectory() as temp_dir_:
        temp_dir = Path(temp_dir_)
        # When
        results = tika.unpack(obj=input_file_path, output_dir=temp_dir, max_depth=max_depth)

        # Then
        assert isinstance(results, list)
        assert len(results) == len(expected_embedded_file_names)

        # ensure all expected files are in the results
        result_paths = set[str]()
        for result in results:
            rel_path = result.file_path.relative_to(temp_dir)
            result_paths.add(str(rel_path))
        assert set(expected_embedded_file_names) == result_paths

        # ensure that all files were unpacked to the correct directory
        for result in results:
            assert result.file_path.exists()
            assert result.file_path.is_file()
            assert len(result.file_path.read_bytes())


def test_unpack_nonexistent_file(tika: Tika) -> None:
    """Test unpacking with an invalid file."""
    # Given
    with tempfile.TemporaryDirectory() as temp_dir_:
        temp_dir = Path(temp_dir_)
        invalid_file = temp_dir / "invalid_file"

        # When/Then
        with pytest.raises(FileNotFoundError, match=str(invalid_file)):
            tika.unpack(invalid_file, output_dir=temp_dir)


@pytest.fixture
def tika_server_unpack_request_params(tika_container: DockerContainer) -> tuple[str, dict[str, str]]:
    host_port = tika_container.get_exposed_port(9998)
    container_ip = tika_container.get_container_host_ip()
    url = f"http://{container_ip}:{host_port}/unpack"

    headers = {"Accept": "application/zip", "Content-Type": "application/octet-stream"}

    return url, headers


UNPACK_SHALLOW_TEST_CASES: list[tuple[str, list[str]]] = [
    ("test_recursive_embedded_docx", ["embed1.zip", "image1.emf"]),
    ("demo_docx", ["image2.png", "image3.png", "image4.png"]),
    ("basic_txt", []),
]


@pytest.mark.parametrize(("fixture_name", "expected_embedded_file_names"), UNPACK_SHALLOW_TEST_CASES)
def test_unpack_compare_with_tika_server(
    tika: Tika,
    request: pytest.FixtureRequest,
    fixture_name: str,
    expected_embedded_file_names: list[str],
    tika_server_unpack_request_params: tuple[str, dict[str, str]],
) -> None:
    """Test unpacking a Word document containing embedded files as compared to the Tika server."""
    input_file_path: Path = request.getfixturevalue(fixture_name)

    url, headers = tika_server_unpack_request_params

    if len(expected_embedded_file_names) == 0:
        pytest.skip("No embedded files to test")
        return

    with tempfile.TemporaryDirectory() as temp_dir_:
        tika_server_output_dir = Path(temp_dir_, "tika_server_output")
        tika_server_output_zip = tika_server_output_dir / "output.zip"
        tika_lib_output_dir = Path(temp_dir_, "tika_lib_output")

        tika_server_output_dir.mkdir(parents=True)
        tika_lib_output_dir.mkdir(parents=True)

        with open(input_file_path, "rb") as input_stream:
            response = requests.put(url, headers=headers, data=input_stream)
            if not response.ok:
                msg = f"Failed to unpack file using Tika server: {response.text}"
                raise RuntimeError(msg)

            # pipe to output zip
            with open(tika_server_output_zip, "wb") as tika_zip_stream:
                tika_zip_stream.write(response.content)

            # unpack the zip
            extract_and_cleanup_zip(tika_server_output_zip)

        # When
        lib_results = tika.unpack(
            obj=input_file_path,
            output_dir=tika_lib_output_dir,
        )

        # Then
        assert len(lib_results) == len(expected_embedded_file_names)
        # ensure that every file found by the Tika server is also found by the library
        for file in os.listdir(tika_server_output_dir):
            assert any(result.file_path.name == file for result in lib_results)
