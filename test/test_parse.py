import io
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, ClassVar, Literal

import pytest
import requests
from jpype import JImplements, JOverride, JString
from testcontainers.core.container import DockerContainer

from test.conftest import ALL_INVALID_DOCS, ALL_VALID_DOCS
from tikara import Tika
from tikara.data_types import TikaMetadata
from tikara.error_handling import TikaError, TikaInputTypeError

if TYPE_CHECKING:
    from org.apache.tika.detect import Detector
    from org.apache.tika.parser import Parser

SKIP_METADATA_KEYS: set[str] = {
    "X-TIKA:Parsed-By-Full-Set",
    "Content-Type-Override",
    "language",
    "Content-Length",
    "X-TIKA:content",
    "X-TIKA:content_handler",
    "X-TIKA:parse_time_millis",
    "X-TIKA:embedded_depth",
}


@pytest.mark.parametrize("input_type", ["string", "path", "bytes", "stream"])
def test_parse_to_string_input_types(
    tika: Tika, demo_docx: Path, input_type: Literal["string", "path", "bytes", "stream"]
) -> None:
    input_obj: str | Path | bytes | BinaryIO
    match input_type:
        case "string":
            input_obj = str(demo_docx)
        case "path":
            input_obj = demo_docx
        case "bytes":
            input_obj = demo_docx.read_bytes()
        case "stream":
            input_obj = io.BytesIO(demo_docx.read_bytes())

    content, metadata = tika.parse(input_obj)
    assert content
    assert metadata
    assert metadata.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.mark.parametrize("output_format", ["txt", "xhtml"])
@pytest.mark.parametrize("input_type", ["string", "path", "bytes", "stream"])
def test_parse_to_file_combinations(
    tika: Tika,
    demo_docx: Path,
    tmp_path: Path,
    input_type: Literal["string", "path", "bytes", "stream"],
    output_format: Literal["txt", "xhtml"],
) -> None:
    input_obj: str | Path | bytes | BinaryIO
    match input_type:
        case "string":
            input_obj = str(demo_docx)
        case "path":
            input_obj = demo_docx
        case "bytes":
            input_obj = demo_docx.read_bytes()
        case "stream":
            input_obj = io.BytesIO(demo_docx.read_bytes())

    output_file = tmp_path / f"output.{output_format}"
    file_path, metadata = tika.parse(
        input_obj,
        output_file=output_file,
        output_format=output_format,
    )

    assert file_path
    assert file_path.exists()
    assert metadata.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    with open(file_path) as f:
        content = f.read()
        assert content


@pytest.mark.parametrize("output_format", ["txt", "xhtml"])
@pytest.mark.parametrize("input_type", ["string", "path", "bytes", "stream"])
@pytest.mark.parametrize(
    "content_type", [None, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
)
def test_parse_to_stream_with_content_type(
    tika: Tika,
    demo_docx: Path,
    input_type: Literal["string", "path", "bytes", "stream"],
    output_format: Literal["txt", "xhtml"],
    content_type: str | None,
) -> None:
    input_obj: str | Path | bytes | BinaryIO
    match input_type:
        case "string":
            input_obj = str(demo_docx)
        case "path":
            input_obj = demo_docx
        case "bytes":
            input_obj = demo_docx.read_bytes()
        case "stream":
            input_obj = io.BytesIO(demo_docx.read_bytes())

    stream, metadata = tika.parse(
        input_obj,
        output_stream=True,
        output_format=output_format,
        content_type=content_type,
    )

    assert stream
    assert metadata
    assert metadata.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    content = stream.read().decode()
    assert content


def test_parse_with_invalid_input(tika: Tika) -> None:
    with pytest.raises(TikaInputTypeError):
        tika.parse(123)  # type: ignore  # noqa: PGH003


def test_parse_with_nonexistent_file(tika: Tika) -> None:
    with pytest.raises(TikaError):
        tika.parse(Path("nonexistent.docx"))


@pytest.mark.parametrize("output_format", ["invalid", "pdf", "doc"])
def test_parse_with_default_output_format(tika: Tika, demo_docx: Path, output_format: str) -> None:
    content, _ = tika.parse(demo_docx, output_format=output_format)  # type: ignore  # noqa: PGH003
    assert content
    assert isinstance(content, str)


@pytest.mark.parametrize(
    ("expected_content_type", "fixture_name"),
    [
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "demo_docx"),
        ("application/pdf", "test_pdf_child_attachments"),
        ("text/plain", "basic_txt"),
        ("text/html", "basic_html"),
    ],
)
def test_parse_different_file_types(
    tika: Tika,
    request: pytest.FixtureRequest,
    expected_content_type: str,
    fixture_name: str,
) -> None:
    test_file: Path = request.getfixturevalue(fixture_name)
    content, metadata = tika.parse(test_file)
    assert content
    assert metadata.content_type
    assert expected_content_type in metadata.content_type


@pytest.fixture
def tika_server_parse_metadata_request_params_norecurse(tika_container: DockerContainer) -> tuple[str, dict[str, str]]:
    host_port = tika_container.get_exposed_port(9998)
    container_ip = tika_container.get_container_host_ip()
    url = f"http://{container_ip}:{host_port}/rmeta"
    headers = {
        "Accept": "application/json",
        "X-Tika-Skip-Embedded": "true",
    }
    return url, headers


@pytest.mark.parametrize(
    ("input_type", "fixture_name", "content_type", "expected_missing"),
    [
        (
            "string",
            "demo_docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            [*SKIP_METADATA_KEYS],
        ),
        (
            "file",
            "demo_docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            [*SKIP_METADATA_KEYS],
        ),
        (
            "stream",
            "demo_docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            [*SKIP_METADATA_KEYS],
        ),
        (
            "string",
            "test_pdf_child_attachments",
            "application/pdf",
            [*SKIP_METADATA_KEYS],
        ),
        (
            "file",
            "test_pdf_child_attachments",
            "application/pdf",
            [*SKIP_METADATA_KEYS],
        ),
        (
            "stream",
            "test_pdf_child_attachments",
            "application/pdf",
            [*SKIP_METADATA_KEYS],
        ),
    ],
)
def test_parse_metadata_compare_with_tika_server(
    input_type: Literal["string", "file", "stream"],
    fixture_name: str,
    content_type: str,
    expected_missing: list[str],
    tika: Tika,
    request: pytest.FixtureRequest,
    tika_server_parse_metadata_request_params_norecurse: tuple[str, dict[str, str]],
) -> None:
    """Test metadata extraction accuracy against Tika server for various file types."""
    test_file: Path = request.getfixturevalue(fixture_name)

    if expected_missing:
        pytest.warns(UserWarning, match=f"{len(expected_missing)} metadata keys are expected to be missing")

    our_metadata: TikaMetadata | None = None
    match input_type:
        case "string":
            _, our_metadata = tika.parse(test_file, input_file_name=test_file.name)
        case "file":
            _, our_metadata = tika.parse(str(test_file.absolute()), input_file_name=test_file.name)
        case "stream":
            with test_file.open("rb") as f:
                _, our_metadata = tika.parse(f, input_file_name=test_file.name)

    assert our_metadata

    url, headers = tika_server_parse_metadata_request_params_norecurse
    headers["Content-Type"] = content_type
    headers["Content-Disposition"] = f"attachment; filename={test_file.absolute()}"

    response = requests.put(url, headers=headers, data=test_file.read_bytes())
    assert response.ok
    tika_server_metadata: dict[str, Any] = response.json()[0]
    # drop the content key from the response
    tika_server_metadata.pop("X-TIKA:content")

    ours_has_but_not_tika = set(our_metadata.raw_metadata.keys()) - set(tika_server_metadata.keys())
    tika_has_but_not_ours = (
        set(tika_server_metadata.keys()) - set(our_metadata.raw_metadata.keys()) - set(expected_missing)
    )

    if ours_has_but_not_tika:
        ours_friendly: dict[str, str] = {
            k: str(v) for k, v in our_metadata.raw_metadata.items() if k in ours_has_but_not_tika
        }
        pytest.fail(f"Ours has but Tika server does not: {ours_friendly}")

    if tika_has_but_not_ours:
        tika_friendly: dict[str, str] = {
            k: str(v) for k, v in tika_server_metadata.items() if k in tika_has_but_not_ours
        }
        pytest.fail(f"Tika server has but ours does not: {tika_friendly}")

    for key, value in our_metadata.raw_metadata.items():
        if key in expected_missing:
            continue
        assert value in tika_server_metadata[key], (
            f"Value mismatch for key: {key}. Tika has: {tika_server_metadata[key]}, but we have: {value}"
        )


@pytest.fixture
def tika_server_parse_content_request_params(tika_container: DockerContainer) -> tuple[str, dict[str, str]]:
    host_port = tika_container.get_exposed_port(9998)
    container_ip = tika_container.get_container_host_ip()
    url = f"http://{container_ip}:{host_port}/tika"
    return url, {}


@pytest.mark.parametrize("input_type", ["string", "path", "bytes", "stream"])
def test_parse_content_compare_with_tika_server(
    tika: Tika,
    demo_docx: Path,
    input_type: Literal["string", "path", "bytes", "stream"],
    tika_server_parse_content_request_params: tuple[str, dict[str, str]],
) -> None:
    """Compare content parsing results with Tika server."""
    url, headers = tika_server_parse_content_request_params

    input_obj: str | Path | bytes | BinaryIO
    match input_type:
        case "string":
            input_obj = str(demo_docx)
        case "path":
            input_obj = demo_docx
        case "bytes":
            input_obj = demo_docx.read_bytes()
        case "stream":
            input_obj = io.BytesIO(demo_docx.read_bytes())

    our_content, _ = tika.parse(input_obj, output_format="txt")

    headers["Accept"] = "text/plain"
    headers["X-Tika-Skip-Embedded"] = "true"
    response = requests.put(url, headers=headers, data=demo_docx.read_bytes())
    assert response.ok

    tika_content: str = response.content.decode("utf-8")

    # Normalize content for comparison
    our_content = (
        re.sub(r"\s+", " ", our_content).strip().rstrip().replace("\n", "").replace("\r", "").replace("\t", "")
    )
    tika_content = (
        re.sub(r"\s+", " ", tika_content).strip().rstrip().replace("\n", "").replace("\r", "").replace("\t", "")
    )

    assert tika_content in our_content


@pytest.fixture
def custom_parser() -> "Parser":
    def get_parsers() -> list["Parser"]:
        from xml.sax import ContentHandler

        from java.io import InputStream
        from java.util import HashSet
        from org.apache.tika.metadata import Metadata
        from org.apache.tika.mime import MediaType
        from org.apache.tika.parser import ParseContext, Parser

        @JImplements(Parser)
        class MarkdownParser:
            def __init__(self) -> None:
                self.supported_types = HashSet()
                self.supported_types.add(MediaType.parse("text/markdown"))

            @JOverride
            def getSupportedTypes(self, context: ParseContext) -> HashSet:  # noqa: N802
                return self.supported_types

            @JOverride
            def parse(
                self, stream: InputStream, handler: ContentHandler, metadata: Metadata, context: ParseContext
            ) -> None:
                bytes_array = bytearray()
                byte = stream.read()
                while byte != -1:
                    bytes_array.append(byte)
                    byte = stream.read()

                content = bytes_array.decode("utf-8")

                # Convert to Java char array using JClass
                chars = JString(content).toCharArray()

                handler.startDocument()
                handler.characters(chars, 0, len(chars))  # type: ignore  # noqa: PGH003
                handler.endDocument()

        return [MarkdownParser()]

    return get_parsers()[0]


@pytest.fixture
def custom_detector() -> "Detector":
    def get_detectors() -> list["Detector"]:
        from java.io import InputStream
        from org.apache.tika.detect import Detector
        from org.apache.tika.metadata import Metadata, TikaCoreProperties
        from org.apache.tika.mime import MediaType

        @JImplements(Detector)
        class MarkdownDetector:
            file_endings: ClassVar[list[str]] = [".md", ".mdx"]
            mime_type: ClassVar[str] = "text/markdown"

            @JOverride
            def detect(self, input_stream: InputStream, metadata: Metadata) -> MediaType:
                # simply check the file extension
                file_name = str(metadata.get(TikaCoreProperties.RESOURCE_NAME_KEY)) or None
                if file_name and file_name.endswith(tuple(self.file_endings)):
                    metadata.set(Metadata.CONTENT_TYPE, self.mime_type)
                    return MediaType.parse(self.mime_type)

                # if we cant figure it out, return the default and tika will try the other detectors
                return MediaType.OCTET_STREAM

        return [MarkdownDetector()]

    return get_detectors()[0]


@pytest.mark.parametrize(
    ("fixture_name", "expected_mime_type", "expected_parser_name_pattern"),
    [
        (
            "demo_docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "DefaultParser",
        ),
        (
            "readme",
            "text/markdown",
            "jdk.proxy",
        ),
    ],
)
def test_parse_custom_parser_and_detector(
    fixture_name: str,
    expected_mime_type: str,
    expected_parser_name_pattern: str,
    request: pytest.FixtureRequest,
    custom_parser: "Parser",
    custom_detector: "Detector",
) -> None:
    test_file: Path = request.getfixturevalue(fixture_name)

    tika = Tika(
        custom_parsers=[custom_parser],
        custom_detectors=[custom_detector],
        custom_mime_types=["text/markdown"],
    )

    content, metadata = tika.parse(test_file)
    assert content
    assert metadata
    assert metadata.content_type
    assert expected_mime_type in metadata.content_type
    assert expected_parser_name_pattern in metadata.raw_metadata["X-TIKA:Parsed-By"]


@pytest.mark.parametrize("input_file_path", ALL_VALID_DOCS)
def test_parse_all_valid_docs_no_errors(tika: Tika, input_file_path: Path) -> None:
    content, metadata = tika.parse(input_file_path)
    assert content
    assert metadata
    assert metadata.content_type
    assert metadata.raw_metadata


@pytest.mark.parametrize("input_file_path", ALL_INVALID_DOCS)
def test_parse_all_invalid_docs_no_errors(tika: Tika, input_file_path: Path) -> None:
    with pytest.raises(TikaError):
        tika.parse(input_file_path)


OCR_PARSE_LANG_DET_PARAMS: list[tuple[Path, str, str | None]] = [
    (Path("./test/data/numbers_gs150.jpg"), "3.75 miles", None),
    (Path("./test/data/stock_gs200.jpg"), "Nasdaq & AMEX", "en"),
    (Path("./test/data/captcha1.jpg"), "chizah", None),
    (Path("./test/data/plaid_c150.jpg"), "Saturdays at 8", "en"),
]


@pytest.mark.parametrize(("input_file_path", "excerpt", "lang"), OCR_PARSE_LANG_DET_PARAMS)
def test_parse_ocr_docs(tika: Tika, input_file_path: Path, excerpt: str, lang: str | None) -> None:
    content, metadata = tika.parse(input_file_path, output_format="txt")
    assert content
    assert metadata
    assert metadata.content_type
    assert metadata.raw_metadata

    assert excerpt in content

    if lang:
        lang_result = tika.detect_language(content)
        assert lang_result
        assert lang_result.language == lang
    else:
        pytest.warns(UserWarning, match=f"Language detection skipped for {input_file_path.name}")
