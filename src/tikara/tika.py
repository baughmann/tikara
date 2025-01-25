from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Literal, overload

from jpype import JProxy

from tikara.java_util import (
    initialize_jvm,
    is_binary_io,
    reader_as_binary_stream,
    wrap_python_stream,
)
from tikara.tika_util import (
    LanguageConfidence,
    TikaraDetectLanguageResult,
    TikaraEmbeddedDocumentExtractor,
    TikaraUnpackedItem,
    _get_metadata,
    metadata_to_dict,
    tika_input_stream,
)

if TYPE_CHECKING:
    from java.io import InputStream  # type: ignore  # noqa: PGH003
    from org.apache.tika.detect import Detector  # type: ignore  # noqa: PGH003
    from org.apache.tika.metadata import Metadata  # type: ignore  # noqa: PGH003
    from org.apache.tika.parser import Parser  # type: ignore  # noqa: PGH003


TikaParseOutputFormat = Literal["txt", "xhtml"]
TikaInputType = str | Path | bytes | BinaryIO


class Tika:
    """The main entrypoint class. Wraps management of the underlying Tika and JVM instances."""

    def _ensure_language_models_loaded(self) -> None:
        if not self._models_loaded:
            self._language_detector.loadModels()
            self._models_loaded = True

    def __init__(
        self,
        *,
        lazy_load: bool = True,
        custom_parsers: list["Parser"] | None = None,
        custom_detectors: list["Detector"] | None = None,
    ) -> None:
        """Creates a new instance of the Tika wrapper.

        Args:
            configuration (TikaConfig, optional): The optional configuration to be used. Default new default config.
            manage_jvm (bool, optional): Whether to manage the JVM lifecycle. Defaults to True.
        """
        self._tika_version: str = "3.0.0"

        initialize_jvm()

        custom_detectors = custom_detectors or []
        custom_parsers = custom_parsers or []

        from org.apache.tika import Tika as JTika  # type: ignore  # noqa: PGH003
        from org.apache.tika.config import TikaConfig as JTikaConfig  # type: ignore  # noqa: PGH003
        from org.apache.tika.detect import DefaultDetector  # type: ignore  # noqa: PGH003
        from org.apache.tika.language.detect import LanguageDetector  # type: ignore  # noqa: PGH003
        from org.apache.tika.parser import AutoDetectParser, DefaultParser  # type: ignore  # noqa: PGH003

        self._j_tika_config = JTikaConfig.getDefaultConfig()

        self._detector = DefaultDetector()
        self._parser = AutoDetectParser(DefaultDetector(), DefaultParser(), *custom_parsers)
        self._tika = JTika(self._detector, self._parser)
        self._language_detector = LanguageDetector.getDefaultLanguageDetector()
        self._models_loaded = False

        if not lazy_load:
            self._ensure_language_models_loaded()

    def _handle_file_output(
        self,
        output_file: Path,
        input_stream: "InputStream",
        metadata: "Metadata",
        output_format: TikaParseOutputFormat,
    ) -> tuple[Path, dict[str, Any]]:
        """Handle parsing with file output."""
        from java.io import FileOutputStream, FileWriter  # type: ignore  # noqa: PGH003
        from org.apache.tika.parser import (  # type: ignore  # noqa: PGH003
            ParseContext,
            Parser,
        )
        from org.apache.tika.sax import (  # type: ignore # noqa: PGH003
            BodyContentHandler,
            ToXMLContentHandler,
        )
        from org.xml.sax import ContentHandler  # type: ignore  # noqa: PGH003

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
            pc.set(Parser, self._parser)
            pc.set(ContentHandler, ch)

            self._parser.parse(input_stream, ch, metadata, pc)

            return output_file, metadata_to_dict(metadata)
        finally:
            if output:
                output.close()

    def _handle_stream_output(
        self,
        input_stream: "InputStream",
        metadata: "Metadata",
        output_format: TikaParseOutputFormat,
    ) -> tuple[BinaryIO, dict[str, Any]]:
        """Handle parsing with stream output."""
        from java.io import ByteArrayOutputStream, OutputStreamWriter  # type: ignore  # noqa: PGH003
        from org.apache.tika.parser import (  # type: ignore  # noqa: PGH003
            ParseContext,
            Parser,
        )
        from org.apache.tika.sax import (  # type: ignore # noqa: PGH003
            BodyContentHandler,
            ToXMLContentHandler,
        )
        from org.xml.sax import ContentHandler  # type: ignore  # noqa: PGH003

        output_stream = ByteArrayOutputStream()
        if output_format == "xhtml":
            ch = ToXMLContentHandler(output_stream, "UTF-8")
        elif output_format == "txt":
            ch = BodyContentHandler(OutputStreamWriter(output_stream, "UTF-8"))
        else:
            msg = f"Unsupported output format: {output_format}"
            raise ValueError(msg)

        pc = ParseContext()
        pc.set(Parser, self._parser)
        pc.set(ContentHandler, ch)

        self._parser.parse(input_stream, ch, metadata, pc)

        return reader_as_binary_stream(output_stream), metadata_to_dict(metadata)

    def _handle_string_output(
        self,
        input_stream: "InputStream",
        metadata: "Metadata",
        output_format: TikaParseOutputFormat,
    ) -> tuple[str, dict[str, Any]]:
        """Handle parsing with string output."""
        from java.io import StringWriter  # type: ignore  # noqa: PGH003
        from org.apache.tika.parser import (  # type: ignore  # noqa: PGH003
            ParseContext,
            Parser,
        )
        from org.apache.tika.sax import (  # type: ignore # noqa: PGH003
            BodyContentHandler,
            RichTextContentHandler,
            ToXMLContentHandler,
        )
        from org.xml.sax import ContentHandler  # type: ignore  # noqa: PGH003

        writer = StringWriter()

        ch = (
            ToXMLContentHandler("UTF-8")
            if output_format == "xhtml"
            else BodyContentHandler(RichTextContentHandler(writer))
        )

        pc = ParseContext()
        pc.set(Parser, self._parser)
        pc.set(ContentHandler, ch)

        self._parser.parse(input_stream, ch, metadata, pc)

        return str(ch.toString()), metadata_to_dict(metadata)

    #
    # MimeType detection
    #
    def detect_mime_type(self, obj: TikaInputType) -> str:
        """Detects the MIME type of the input object.

        Args:
            obj (str | bytes | Path | BinaryIO): The input object to detect the MIME type of.

        Returns:
            str: The detected MIME type.
        """

        from java.io import ByteArrayInputStream, InputStream  # type: ignore  # noqa: PGH003
        from java.nio.file import Path as JPath  # type: ignore  # noqa: PGH003

        input_stream: InputStream | None = None
        input_file: Path | None = None

        if isinstance(obj, str | Path):
            input_file = Path(obj)
        elif isinstance(obj, bytes):
            input_stream = ByteArrayInputStream(obj)
        elif is_binary_io(obj):
            input_stream = wrap_python_stream(obj)
        else:
            msg = f"Unsupported input type: {type(obj)}"
            raise TypeError(msg)

        if input_file and not input_file.exists():
            msg = f"File not found: {input_file}"
            raise FileNotFoundError(msg)

        try:
            if input_stream:
                return str(self._tika.detect(input_stream))
            if input_file:
                java_path = JPath.of(str(input_file))
                return str(self._tika.detect(java_path))
            msg = "Unsupported input type"
            raise ValueError(msg)
        finally:
            if isinstance(input_stream, InputStream):
                input_stream.close()

    #
    # Language detection
    #
    def detect_language(
        self,
        content: str,
    ) -> TikaraDetectLanguageResult:
        """Detects the language of the given string content.

        Args:
            content (str): The string content to detect the language of.

        Returns:
            tikaraDetectLanguageResult: The detected language with some confidence information.
        """

        self._ensure_language_models_loaded()

        result = self._language_detector.detect(content)

        return TikaraDetectLanguageResult(
            language=str(result.getLanguage()),
            confidence=LanguageConfidence(str(result.getConfidence().name())),
            raw_score=float(result.getRawScore()),
        )

    def unpack(
        self,
        obj: TikaInputType,
        output_dir: Path,
        *,
        max_depth: int = 1,
        input_file_name: str | Path | None = None,
        content_type: str | None = None,
    ) -> list[TikaraUnpackedItem]:
        """Unpacks embedded documents from a parent document. Can do so recursively to a specified depth.

        Args:
            obj (str | Path | bytes | BinaryIO): The path to the parent document.
            output_dir (Path): The directory to write the extracted documents to.
            max_depth (int, optional): The maximum depth to unpack. Defaults to 1.
            input_file_name (str | Path | None, optional): If obj is not a file, the name of the file that the content
                is coming from. This helps tika extract metadata. Defaults to None.
            content_type (str | None, optional): The mime type of the content if known. This helps Tika extract metadata. Defaults to None.

        Raises:
            FileNotFoundError: If the input file is not found.
            ValueError: If the input is not a file.

        Returns:
            list[tikaraUnpackedItem]: The list extracted document paths and metadata.
        """  # noqa: E501

        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        from org.apache.tika.extractor import EmbeddedDocumentExtractor  # type: ignore  # noqa: PGH003
        from org.apache.tika.parser import ParseContext, Parser  # type: ignore  # noqa: PGH003
        from org.xml.sax import ContentHandler  # type: ignore  # noqa: PGH003
        from org.xml.sax.helpers import DefaultHandler  # type: ignore  # noqa: PGH003

        metadata = _get_metadata(obj=obj, input_file_name=input_file_name, content_type=content_type)

        ch = DefaultHandler()
        pc = ParseContext()
        pc.set(Parser, self._parser)
        pc.set(ContentHandler, ch)
        extractor = TikaraEmbeddedDocumentExtractor(
            parse_context=pc,
            parser=self._parser,
            output_dir=output_dir,
            max_depth=max_depth,
        )

        pc.set(
            EmbeddedDocumentExtractor,
            JProxy(
                EmbeddedDocumentExtractor,
                inst=extractor,
            ),
        )

        with tika_input_stream(obj, metadata=metadata) as input_stream:
            self._parser.parse(input_stream, ch, metadata, pc)

            return extractor.get_results()

    @overload
    def parse(
        self,
        obj: TikaInputType,
        *,
        output_format: TikaParseOutputFormat = "xhtml",
        input_file_name: str | Path | None = None,
        content_type: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Parses the input object and returns the string content and metadata.

        Args:
            obj (str | Path | bytes | BinaryIO): The input object to parse.
            output_format (Literal["txt", "xhtml"], optional): The format of the output content. Defaults to structured "xhtml"
            input_file_name (str | Path | None, optional): The name of the input file if known (and not already providing one). This helps Tika parse the file. Defaults to None.
            content_type (str | None, optional): content_type (str | None, optional): The optional mimetype of the content if known. This helps tika parse the file. Defaults to None.

        Returns:
            tuple[str, dict[str, Any]]: _description_
        """  # noqa: E501

        ...

    @overload
    def parse(
        self,
        obj: TikaInputType,
        *,
        output_file: Path | str,
        output_format: TikaParseOutputFormat = "xhtml",
        input_file_name: str | Path | None = None,
        content_type: str | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        """Parses the input object and the path to the output file and returns the metadata.

        Args:
            obj (str | Path | bytes | BinaryIO): The input object to parse.
            output_file (Path | str): The path to write the output content to. Preferably, ending in .txt or .xhtml.
            output_format (Literal["txt", "xhtml"], optional): The format of the output content. Defaults to structured "xhtml".
            input_file_name (str | Path | None, optional): The name of the input file if known (and not already providing one). This helps Tika parse the file. Defaults to None.
            content_type (str | None, optional): The optional mimetype of the content if known. This helps tika parse the file. Defaults to None.

        Returns:
            tuple[BinaryIO, dict[str, Any]]: The output content stream and metadata.
        """  # noqa: E501

        ...

    @overload
    def parse(
        self,
        obj: TikaInputType,
        *,
        output_stream: bool,
        output_format: TikaParseOutputFormat = "xhtml",
        input_file_name: str | Path | None = None,
        content_type: str | None = None,
    ) -> tuple[BinaryIO, dict[str, Any]]:
        """Parses the input object and returns the contents stream and metadata.

        Args:
            obj (str | Path | bytes | BinaryIO): The input object to parse.
            output_stream (bool): Whether to return the content as a stream. Defaults to False.
            output_format (Literal["txt", "xhtml"], optional): The format of the output content. The format of the output content. Defaults to structured "xhtml".
            input_file_name (str | Path | None, optional): The name of the input file if known (and not already providing one). This helps Tika parse the file. Defaults to None.
            content_type (str | None, optional): The optional mimetype of the content if known. This helps tika parse the file. Defaults to None.

        Returns:
            tuple[BinaryIO, dict[str, Any]]: The output content stream and metadata.
        """  # noqa: E501

        ...

    def _prepare_output_file(self, output_file: Path | str | None, output_format: TikaParseOutputFormat) -> Path | None:
        if output_file:
            if isinstance(output_file, str):
                output_file = Path(output_file)
            if not output_file.parent.exists():
                output_file.parent.mkdir(parents=True)
            if output_file.suffix:
                output_file = output_file.with_suffix(f".{output_format}")
            return output_file

        return None

    def parse(  # noqa: PLR0913
        self,
        obj: TikaInputType,
        *,
        output_stream: bool = False,
        output_format: TikaParseOutputFormat = "xhtml",
        output_file: Path | str | None = None,
        input_file_name: str | Path | None = None,
        content_type: str | None = None,
    ) -> tuple[str | Path | BinaryIO, dict[str, Any]]:
        output_mode: Literal["string", "file", "stream"]
        if output_stream:
            output_mode = "stream"
        elif output_file:
            output_mode = "file"
        else:
            output_mode = "string"

        output_file = self._prepare_output_file(output_file=output_file, output_format=output_format)
        if output_mode == "file" and not output_file:
            msg = "output_file is required when mode is 'file'"
            raise ValueError(msg)

        # Create initial metadata
        metadata = _get_metadata(
            obj=obj,
            input_file_name=input_file_name,
            content_type=content_type,
        )

        # Create input stream
        with tika_input_stream(obj, metadata=metadata) as input_stream:
            match output_mode:
                case "file":
                    if not output_file:
                        msg = "output_file is required when mode is 'file'"
                        raise ValueError(msg)
                    return self._handle_file_output(
                        output_file=output_file,
                        input_stream=input_stream,
                        metadata=metadata,
                        output_format=output_format,
                    )
                case "stream":
                    return self._handle_stream_output(
                        input_stream=input_stream,
                        metadata=metadata,
                        output_format=output_format,
                    )
                case "string":
                    return self._handle_string_output(
                        input_stream=input_stream,
                        metadata=metadata,
                        output_format=output_format,
                    )
                case _:
                    msg = f"Unsupported mode: {output_mode}"
                    raise ValueError(msg)
