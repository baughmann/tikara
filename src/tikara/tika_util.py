import logging
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from tikara.java_util import file_output_stream, is_binary_io, wrap_python_stream

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from java.io import (  # type: ignore  # noqa: PGH003
        InputStream,
    )
    from org.apache.tika.io import TikaInputStream  # type: ignore  # noqa: PGH003
    from org.apache.tika.metadata import Metadata  # type: ignore  # noqa: PGH003
    from org.apache.tika.parser import ParseContext, Parser  # type: ignore  # noqa: PGH003
    from org.xml.sax import ContentHandler  # type: ignore  # noqa: PGH003


@dataclass(frozen=True, kw_only=True)
class TikaraUnpackedItem:
    metadata: dict[str, str]
    file_path: Path


@unique
class LanguageConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


@dataclass(frozen=True, kw_only=True)
class TikaraDetectLanguageResult:
    language: str
    confidence: LanguageConfidence
    raw_score: float


def metadata_to_dict(metadata: "Metadata") -> dict[str, str]:
    return {str(key): str(metadata.get(key)) for key in metadata.names()}


class TikaraEmbeddedDocumentExtractor:
    """
    Extracts embedded documents from a parent document using Apache Tika.
    Writes the extracted documents to the specified output directory and keeps track of the metadata and file
    paths extracted.
    """

    def __init__(
        self,
        parse_context: "ParseContext",
        parser: "Parser",
        output_dir: Path,
        max_depth: int,
    ) -> None:
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.current_depth = 0
        self._parser = parser
        self._results: list[TikaraUnpackedItem] = []
        self._context = parse_context

    def parseEmbedded(  # noqa: N802
        self,
        stream: "InputStream",
        handler: "ContentHandler",
        metadata: "Metadata",
        recurse: bool,  # noqa: FBT001
    ) -> bool:
        try:
            from org.apache.tika.metadata import Metadata, TikaCoreProperties  # type: ignore  # noqa: PGH003

            if self.current_depth >= self.max_depth:
                return False
            name = (
                metadata.get(TikaCoreProperties.RESOURCE_NAME_KEY)
                or metadata.get(TikaCoreProperties.EMBEDDED_RELATIONSHIP_ID)
                or f"embedded_{len(self._results)}"
            )

            output_path = Path(self.output_dir, str(name))

            with file_output_stream(output_path) as fos, tika_input_stream(stream) as tika_stream:
                while True:
                    bytes_read = tika_stream.read()
                    if bytes_read == -1:
                        break
                    fos.write(bytes_read)

            self._results.append(
                TikaraUnpackedItem(
                    file_path=output_path,
                    metadata=metadata_to_dict(metadata),
                )
            )

            if recurse:
                self.current_depth += 1
                try:
                    with tika_input_stream(output_path, metadata=metadata) as nested_stream:
                        self._parser.parse(nested_stream, handler, Metadata(), self._context)
                finally:
                    self.current_depth -= 1

            return True  # noqa: TRY300
        except Exception as e:
            logger.exception("Error occurred attempted to parse embedded document", exc_info=e)
            raise

    def shouldParseEmbedded(self, metadata: "Metadata") -> bool:  # noqa: N802
        return True

    def get_results(self) -> list[TikaraUnpackedItem]:
        return self._results


def _get_metadata(
    obj: str | bytes | Path | BinaryIO,
    input_stream: "TikaInputStream | None" = None,
    input_file_name: str | Path | None = None,
    content_type: str | None = None,
) -> "Metadata":
    """
    Fills the metadata object with the content type and resource name of the input stream.

    Replicates TikaServer's `org.apache.tika.server.core.resource.TikaResource.fillMetadata` logic
    """
    from org.apache.tika.metadata import Metadata, TikaCoreProperties  # type: ignore  # noqa: PGH003
    from org.apache.tika.mime import MimeTypes  # type: ignore  # noqa: PGH003

    metadata = Metadata()

    file_name = obj if isinstance(obj, Path | str) else input_file_name
    if file_name:
        metadata.add(TikaCoreProperties.RESOURCE_NAME_KEY, str(file_name))

    if content_type:
        metadata.add(Metadata.CONTENT_TYPE, content_type)
        metadata.add(TikaCoreProperties.CONTENT_TYPE_USER_OVERRIDE, content_type)

    if input_stream:
        mime_types = MimeTypes.getDefaultMimeTypes()
        mime_type = mime_types.detect(input_stream, metadata)
        metadata.add(Metadata.CONTENT_TYPE, mime_type.toString())

    return metadata


@contextmanager
def tika_input_stream(
    obj: "str | bytes | Path | BinaryIO | InputStream", *, metadata: "Metadata | None" = None
) -> Generator["TikaInputStream", None, None]:
    """Wraps arbitrary input objects as TikaInputStreams.

    Args:
        obj (str | bytes | Path | BinaryIO): The input object to wrap.
        metadata (Metadata | None): The metadata to associate with the input stream. Defaults to empty metadata.

    Yields:
        TikaInputStream: The wrapped input stream.
    """
    from java.io import ByteArrayInputStream, Closeable, InputStream, PipedInputStream  # type: ignore  # noqa: PGH003
    from java.nio.file import NoSuchFileException  # type: ignore # noqa: PGH003
    from java.nio.file import Path as JPath  # type: ignore  # noqa: PGH003
    from org.apache.tika.io import TemporaryResources, TikaInputStream  # type: ignore  # noqa: PGH003
    from org.apache.tika.metadata import Metadata  # type: ignore  # noqa: PGH003

    metadata = metadata or Metadata()

    input_obj: PipedInputStream | ByteArrayInputStream | InputStream | JPath
    if isinstance(obj, str | Path):
        input_obj = JPath.of(str(obj))  # technically supports network resources
    elif isinstance(obj, bytes):
        input_obj = ByteArrayInputStream(obj)
    elif isinstance(obj, InputStream):
        input_obj = obj
    elif is_binary_io(obj):
        input_obj = wrap_python_stream(obj)
    else:
        msg = f"Unsupported input type: {type(obj)}"
        raise TypeError(msg)

    try:
        if isinstance(input_obj, InputStream):
            yield TikaInputStream.get(input_obj, TemporaryResources(), metadata)
        else:
            yield TikaInputStream.get(input_obj, metadata)
    except NoSuchFileException as e:
        raise FileNotFoundError(e.message()) from e
    finally:
        if isinstance(input_obj, Closeable):
            input_obj.close()
