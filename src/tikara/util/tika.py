"""Collection of utility function and classes for interacting with the underlying Apache Tika library."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, Protocol, Self

from jpype import JImplements, JOverride

from tikara.data_types import TikaMetadata, TikaParseOutputFormat, TikaUnpackedItem
from tikara.util.java import _file_output_stream, _is_binary_io, _wrap_python_stream, reader_as_binary_stream
from tikara.util.misc import _validate_input_file

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from java.io import (
        InputStream,
    )
    from org.apache.tika.io import TikaInputStream
    from org.apache.tika.metadata import Metadata
    from org.apache.tika.parser import ParseContext, Parser
    from org.xml.sax import ContentHandler


class _RecursiveEmbeddedDocumentExtractor(Protocol):
    """
    Extracts embedded documents from a parent document using Apache Tika.

    Writes the extracted documents to the specified output directory and keeps track of the metadata and file
    paths extracted.
    """

    _max_depth: int
    _current_depth: int

    def parseEmbedded(  # noqa: N802
        self,
        stream: "InputStream",
        handler: "ContentHandler",
        metadata: "Metadata",
        recurse: bool,  # noqa: FBT001
    ) -> bool:
        """Parse an embedded document.

        Args:
            stream (InputStream): The Java input stream of the embedded document.
            handler (ContentHandler): The content handler to use for parsing.
            metadata (Metadata): The metadata of the embedded document.
            recurse (bool): Whether to recursively parse embedded documents.

        Returns:
            bool: Whether the embedded document was successfully parsed.
        """
        ...

    def shouldParseEmbedded(self, metadata: "Metadata") -> bool:  # noqa: N802
        """Determine whether an embedded document should be parsed.

        Args:
            metadata (Metadata): The metadata of the embedded document.

        Returns:
            bool: Whether the embedded document should be parsed.
        """
        ...

    def get_results(self) -> list[TikaUnpackedItem]:
        """Return the list of unpacked embedded documents.

        Returns:
            list[TikaUnpackedItem]: The list of unpacked embedded documents.
        """
        ...

    @classmethod
    def create(
        cls,
        parse_context: "ParseContext",
        parser: "Parser",
        output_dir: Path,
        max_depth: int,
    ) -> Self:
        """Create a new instance of the underlying Java extractor class.

        Args:
            parse_context (ParseContext): The parse context to use.
            parser (Parser): The parser to use.
            output_dir (Path): The output directory to write unpacked embedded documents to.
            max_depth (int): The maximum depth to recurse when unpacking embedded documents.

        Returns:
            Self: The new instance of the extractor that can be passed to the Java side.
        """
        from org.apache.tika.extractor import EmbeddedDocumentExtractor
        from org.apache.tika.metadata import Metadata, TikaCoreProperties

        @JImplements(EmbeddedDocumentExtractor)
        class RecursiveEmbeddedDocumentExtractorImpl(_RecursiveEmbeddedDocumentExtractor):
            def __init__(
                self,
                parse_context: "ParseContext",
                parser: "Parser",
                output_dir: Path,
                max_depth: int,
            ) -> None:
                self.output_dir = output_dir
                self._max_depth = max_depth
                self._current_depth = 0
                self._parser = parser
                self._results: list[TikaUnpackedItem] = []
                self._context = parse_context

            @JOverride
            def parseEmbedded(  # noqa: N802
                self,
                stream: "InputStream",
                handler: "ContentHandler",
                metadata: "Metadata",
                recurse: bool,  # noqa: FBT001
            ) -> bool:
                try:
                    if self._current_depth >= self._max_depth:
                        return False
                    name = (
                        metadata.get(TikaCoreProperties.RESOURCE_NAME_KEY)
                        or metadata.get(TikaCoreProperties.EMBEDDED_RELATIONSHIP_ID)
                        or f"embedded_{len(self._results)}"
                    )

                    output_path = Path(self.output_dir, str(name))

                    with _file_output_stream(output_path) as fos, _tika_input_stream(stream) as tika_stream:
                        while True:
                            bytes_read = tika_stream.read()
                            if bytes_read == -1:
                                break
                            fos.write(bytes_read)

                    self._results.append(
                        TikaUnpackedItem(
                            file_path=output_path,
                            metadata=TikaMetadata._from_java_metadata(metadata),
                        )
                    )

                    if recurse:
                        self._current_depth += 1
                        try:
                            with _tika_input_stream(output_path, metadata=metadata) as nested_stream:
                                self._parser.parse(nested_stream, handler, Metadata(), self._context)
                        finally:
                            self._current_depth -= 1

                    return True  # noqa: TRY300
                except Exception as e:
                    logger.exception("Error occurred attempted to parse embedded document", exc_info=e)
                    raise

            @JOverride
            def shouldParseEmbedded(self, metadata: "Metadata") -> bool:  # noqa: N802
                return True

            def get_results(self) -> list[TikaUnpackedItem]:
                return self._results

        return RecursiveEmbeddedDocumentExtractorImpl(parse_context, parser, output_dir, max_depth)


def _get_metadata(
    obj: str | bytes | Path | BinaryIO,
    input_stream: "TikaInputStream | None" = None,
    input_file_name: str | Path | None = None,
    content_type: str | None = None,
) -> "Metadata":
    """
    Fill the metadata object with the content type and resource name of the input stream.

    Replicates TikaServer's `org.apache.tika.server.core.resource.TikaResource.fillMetadata` logic
    """
    from org.apache.tika.metadata import Metadata, TikaCoreProperties
    from org.apache.tika.mime import MimeTypes

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
def _tika_input_stream(
    obj: "str | bytes | Path | BinaryIO | InputStream", *, metadata: "Metadata | None" = None
) -> Generator["TikaInputStream", None, None]:
    """Wrap arbitrary input objects as TikaInputStreams.

    Args:
        obj (str | bytes | Path | BinaryIO): The input object to wrap.
        metadata (Metadata | None): The metadata to associate with the input stream. Defaults to empty metadata.

    Yields:
        TikaInputStream: The wrapped input stream.
    """
    from java.io import ByteArrayInputStream, Closeable, InputStream, PipedInputStream
    from java.nio.file import Path as JPath
    from org.apache.tika.io import TemporaryResources, TikaInputStream
    from org.apache.tika.metadata import Metadata

    metadata = metadata or Metadata()

    input_obj: PipedInputStream | ByteArrayInputStream | InputStream | JPath
    if isinstance(obj, str | Path):
        _validate_input_file(obj)
        input_obj = JPath.of(str(obj))  # technically supports network resources
    elif isinstance(obj, bytes):
        input_obj = ByteArrayInputStream(obj)
    elif isinstance(obj, InputStream):
        input_obj = obj
    elif _is_binary_io(obj):
        input_obj = _wrap_python_stream(obj)
    else:
        msg = f"Unsupported input type: {type(obj)}"
        raise TypeError(msg)

    try:
        if isinstance(input_obj, InputStream):
            yield TikaInputStream.get(input_obj, TemporaryResources(), metadata)
        else:
            yield TikaInputStream.get(input_obj, metadata)
    finally:
        if isinstance(input_obj, Closeable):
            input_obj.close()


def _handle_file_output(
    parser: "Parser",
    output_file: Path,
    input_stream: "InputStream",
    metadata: "Metadata",
    output_format: TikaParseOutputFormat,
) -> tuple[Path, TikaMetadata]:
    """Handle parsing with file output."""
    from java.io import FileOutputStream, FileWriter
    from org.apache.tika.parser import (
        ParseContext,
        Parser,
    )
    from org.apache.tika.sax import (
        BodyContentHandler,
        ToXMLContentHandler,
    )
    from org.xml.sax import ContentHandler

    output: FileOutputStream | FileWriter | None = None
    try:
        if output_format == "xhtml":
            output = FileOutputStream(str(output_file))
            ch = ToXMLContentHandler(output, "UTF-8")
        elif output_format == "txt":
            output = FileWriter(str(output_file))
            ch = BodyContentHandler(output)
        else:
            msg = f"Unsupported output format: {output_format}"
            raise ValueError(msg)

        pc = ParseContext()
        pc.set(Parser, parser)
        pc.set(ContentHandler, ch)

        parser.parse(input_stream, ch, metadata, pc)

        return output_file, TikaMetadata._from_java_metadata(metadata)
    finally:
        if output:
            output.close()


def _handle_stream_output(
    parser: "Parser",
    input_stream: "InputStream",
    metadata: "Metadata",
    output_format: TikaParseOutputFormat,
) -> tuple[BinaryIO, TikaMetadata]:
    """Handle parsing with stream output."""
    from java.io import ByteArrayOutputStream, OutputStreamWriter
    from org.apache.tika.parser import (
        ParseContext,
        Parser,
    )
    from org.apache.tika.sax import (  # type: ignore # noqa: PGH003
        BodyContentHandler,
        ToXMLContentHandler,
    )
    from org.xml.sax import ContentHandler

    output_stream = ByteArrayOutputStream()
    if output_format == "xhtml":
        ch = ToXMLContentHandler(output_stream, "UTF-8")
    elif output_format == "txt":
        ch = BodyContentHandler(OutputStreamWriter(output_stream, "UTF-8"))
    else:
        msg = f"Unsupported output format: {output_format}"
        raise ValueError(msg)

    pc = ParseContext()
    pc.set(Parser, parser)
    pc.set(ContentHandler, ch)

    parser.parse(input_stream, ch, metadata, pc)

    return reader_as_binary_stream(output_stream), TikaMetadata._from_java_metadata(metadata)


def _handle_string_output(
    parser: "Parser",
    input_stream: "InputStream",
    metadata: "Metadata",
    output_format: TikaParseOutputFormat,
) -> tuple[str, TikaMetadata]:
    """Handle parsing with string output."""
    from java.io import StringWriter
    from org.apache.tika.parser import (
        ParseContext,
        Parser,
    )
    from org.apache.tika.sax import (  # type: ignore # noqa: PGH003
        BodyContentHandler,
        RichTextContentHandler,
        ToXMLContentHandler,
    )
    from org.xml.sax import ContentHandler

    writer = StringWriter()

    ch = (
        ToXMLContentHandler("UTF-8") if output_format == "xhtml" else BodyContentHandler(RichTextContentHandler(writer))
    )

    pc = ParseContext()
    pc.set(Parser, parser)
    pc.set(ContentHandler, ch)

    parser.parse(input_stream, ch, metadata, pc)

    return str(ch.toString()), TikaMetadata._from_java_metadata(metadata)
