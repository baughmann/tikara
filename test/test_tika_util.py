from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, cast
from unittest.mock import Mock

import pytest

from tikara.data_types import TikaLanguageConfidence, TikaMetadata
from tikara.error_handling import TikaInputTypeError
from tikara.util.tika import (
    _RecursiveEmbeddedDocumentExtractor,
    _tika_input_stream,
)

if TYPE_CHECKING:
    from org.apache.tika.metadata import Metadata  # type: ignore  # noqa: PGH003


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def sample_metadata() -> "Metadata":
    from org.apache.tika.metadata import Metadata  # type: ignore  # noqa: PGH003

    metadata = Metadata()
    metadata.add("key1", "value1")
    metadata.add("key2", "value2")
    return metadata


def test_metadata_to_dict(sample_metadata: "Metadata") -> None:
    result = TikaMetadata._metadata_to_dict(sample_metadata)
    assert result == {"key1": "value1", "key2": "value2"}


def test_language_confidence_enum() -> None:
    assert TikaLanguageConfidence.HIGH == "HIGH"
    assert TikaLanguageConfidence.MEDIUM == "MEDIUM"
    assert TikaLanguageConfidence.LOW == "LOW"
    assert TikaLanguageConfidence.NONE == "NONE"


def test_tika_input_stream_with_path(temp_dir: Path) -> None:
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")

    with _tika_input_stream(test_file) as tis:
        content = []
        while (byte := tis.read()) != -1:
            content.append(byte)
        text = bytes(content).decode("utf-8")
        assert text == "test content"


def test_tika_input_stream_with_bytes() -> None:
    test_bytes = b"test content"
    with _tika_input_stream(test_bytes) as tis:
        content = []
        while (byte := tis.read()) != -1:
            content.append(byte)
        assert bytes(content) == test_bytes


def test_tika_input_stream_with_binary_io() -> None:
    bio: BinaryIO = BytesIO(b"test content")
    with _tika_input_stream(bio) as tis:
        content = []
        while (byte := tis.read()) != -1:
            content.append(byte)
        assert bytes(content) == b"test content"


def test_tika_input_stream_invalid_input() -> None:
    with pytest.raises(TikaInputTypeError), _tika_input_stream(123):  # type: ignore  # noqa: PGH003
        pass


class TestRecursiveEmbeddedDocumentExtractor:
    @pytest.fixture
    def extractor(self, temp_dir: Path) -> _RecursiveEmbeddedDocumentExtractor:
        from org.apache.tika.parser import ParseContext, Parser  # type: ignore  # noqa: PGH003

        parse_context = ParseContext()
        parser = cast(Parser, Mock())  # You'll need to properly mock this
        return _RecursiveEmbeddedDocumentExtractor.create(
            parse_context=parse_context, parser=parser, output_dir=temp_dir, max_depth=3
        )

    def test_parse_embedded_basic(self, extractor: _RecursiveEmbeddedDocumentExtractor, temp_dir: Path) -> None:
        from java.io import ByteArrayInputStream  # type: ignore # noqa: PGH003
        from org.apache.tika.metadata import Metadata, TikaCoreProperties  # type: ignore  # noqa: PGH003
        from org.xml.sax import ContentHandler  # type: ignore # noqa: PGH003

        metadata = Metadata()
        metadata.add(TikaCoreProperties.RESOURCE_NAME_KEY, "test.txt")

        test_stream = ByteArrayInputStream(b"test content")
        handler = cast(ContentHandler, Mock())

        result = extractor.parseEmbedded(test_stream, handler, metadata, recurse=False)
        assert result is True

        results = extractor.get_results()
        assert len(results) == 1
        assert results[0].file_path.exists()
        assert results[0].file_path.read_bytes() == b"test content"

    def test_parse_embedded_max_depth(self, extractor: _RecursiveEmbeddedDocumentExtractor) -> None:
        from java.io import ByteArrayInputStream  # type: ignore # noqa: PGH003
        from org.apache.tika.metadata import Metadata  # type: ignore  # noqa: PGH003
        from org.xml.sax import ContentHandler  # type: ignore # noqa: PGH003

        extractor._current_depth = extractor._max_depth
        metadata = Metadata()
        test_stream = ByteArrayInputStream(b"test")
        handler = cast(ContentHandler, Mock())

        result = extractor.parseEmbedded(test_stream, handler, metadata, recurse=True)
        assert result is False

    def test_should_parse_embedded(self, extractor: _RecursiveEmbeddedDocumentExtractor) -> None:
        from org.apache.tika.metadata import Metadata  # type: ignore  # noqa: PGH003

        metadata = Metadata()
        assert extractor.shouldParseEmbedded(metadata) is True
