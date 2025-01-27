from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pytest
import requests
from testcontainers.core.container import DockerContainer

from tikara import Tika
from tikara.error_handling import TikaInputArgumentsError, TikaInputFileNotFoundError

TEST_FILES = {
    "txt": ("plain.txt", "Hello world", "text/plain"),
    "html": ("page.html", "<html><body>Hello</body></html>", "text/html"),
    "xml": ("config.xml", "<?xml version='1.0'?><root></root>", "application/xml"),
}


class TestDetectMimeType:
    @pytest.mark.parametrize(
        ("ext", "filename", "content", "expected_type"),
        [(ext, data[0], data[1], data[2]) for ext, data in TEST_FILES.items()],
    )
    def test_detect_mime_type_path(
        self,
        tika: Tika,
        ext: str,
        filename: str,
        content: str,
        expected_type: str,
        tmp_path: Path,
    ) -> None:
        file_path = tmp_path / filename
        file_path.write_text(content)
        result = tika.detect_mime_type(file_path)
        assert isinstance(result, str | bytes)
        result_str = result if isinstance(result, str) else result.decode()
        assert expected_type == result_str.casefold()

    @pytest.mark.parametrize(
        ("ext", "filename", "content", "expected_type"),
        [(ext, data[0], data[1], data[2]) for ext, data in TEST_FILES.items()],
    )
    def test_detect_mime_type_str(
        self,
        tika: Tika,
        ext: str,
        filename: str,
        content: str,
        expected_type: str,
        tmp_path: Path,
    ) -> None:
        file_path = tmp_path / filename
        file_path.write_text(content)
        result = tika.detect_mime_type(str(file_path))
        assert isinstance(result, str | bytes)
        result_str = result if isinstance(result, str) else result.decode()
        assert expected_type == result_str.casefold()

    @pytest.mark.parametrize(
        ("content", "expected_type"),
        [(data[1], data[2]) for data in TEST_FILES.values()],
    )
    def test_detect_mime_type_bytes(
        self,
        tika: Tika,
        content: str,
        expected_type: str,
    ) -> None:
        result = tika.detect_mime_type(content.encode())
        assert isinstance(result, str | bytes)
        result_str = result if isinstance(result, str) else result.decode()
        assert expected_type == result_str.casefold()

    @pytest.mark.parametrize(
        ("content", "expected_type"),
        [(data[1], data[2]) for data in TEST_FILES.values()],
    )
    def test_detect_mime_type_binary_io(
        self,
        tika: Tika,
        content: str,
        expected_type: str,
    ) -> None:
        bio: BinaryIO = BytesIO(content.encode())
        result = tika.detect_mime_type(bio)
        assert isinstance(result, str | bytes)
        result_str = result if isinstance(result, str) else result.decode()
        assert expected_type == result_str.casefold()

    def test_detect_mime_type_invalid_type(self, tika: Tika) -> None:
        with pytest.raises(TikaInputArgumentsError):
            tika.detect_mime_type(123)  # type: ignore  # noqa: PGH003

    def test_detect_mime_type_nonexistent_file(self, tika: Tika) -> None:
        with pytest.raises(TikaInputFileNotFoundError):
            tika.detect_mime_type(Path("/nonexistent/file"))

    @pytest.fixture
    def tika_server_detect_language_request_params(self, tika_container: DockerContainer) -> tuple[str, dict[str, str]]:
        host_port = tika_container.get_exposed_port(9998)
        container_ip = tika_container.get_container_host_ip()
        url = f"http://{container_ip}:{host_port}/detect/stream"

        headers = {"Accept": "text/plain", "Content-Type": "application/octet-stream"}

        return url, headers

    @pytest.mark.parametrize(
        ("ext", "filename", "content", "expected_type"),
        [(ext, data[0], data[1], data[2]) for ext, data in TEST_FILES.items()],
    )
    def test_detect_mime_type_compare_with_tika_server(
        self,
        tika: Tika,
        ext: str,
        filename: str,
        content: str,
        expected_type: str,
        tmp_path: Path,
        tika_server_detect_language_request_params: tuple[str, dict[str, str]],
    ) -> None:
        if expected_type == "application/json":
            pytest.skip(
                "Tika server returns 'text/plain' for JSON files, even when provided with the filename and mime type"
            )

        file_path = tmp_path / filename
        file_path.write_text(content)

        result = tika.detect_mime_type(file_path)
        assert isinstance(result, str | bytes)
        result_str = result if isinstance(result, str) else result.decode()
        assert expected_type == result_str.casefold()

        url, headers = tika_server_detect_language_request_params
        headers["Content-Disposition"] = f"attachment; filename={filename}"

        result_server = requests.put(url, headers=headers, data=content.encode())
        assert result_server.text == expected_type
