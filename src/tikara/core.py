from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Literal, overload

from jpype import JProxy

from tikara.util.java import (
    initialize_jvm,
    is_binary_io,
    wrap_python_stream,
)
from tikara.util.tika import (
    LanguageConfidence,
    RecursiveEmbeddedDocumentExtractor,
    TikaInputType,
    TikaParseOutputFormat,
    TikaraDetectLanguageResult,
    TikaraUnpackedItem,
    _get_metadata,
    _handle_file_output,
    _handle_stream_output,
    _handle_string_output,
    tika_input_stream,
)

if TYPE_CHECKING:
    from org.apache.tika.detect import Detector
    from org.apache.tika.parser import Parser


class Tika:
    """The main entrypoint class. Wraps management of the underlying Tika and JVM instances."""

    def _ensure_language_models_loaded(self) -> None:
        if not self._models_loaded:
            self._language_detector.loadModels()
            self._models_loaded = True

    def __init__(  # noqa: PLR0913
        self,
        *,
        lazy_load: bool = True,
        custom_parsers: list["Parser"] | Callable[[], list["Parser"]] | None = None,
        custom_detectors: list["Detector"] | Callable[[], list["Detector"]] | None = None,
        custom_mime_types: list[str] | None = None,
        extra_jars: list[Path] | None = None,
        tika_jar_override: Path | None = None,
    ) -> None:
        """Initialize a new Tika wrapper instance.

        This class provides a Python interface to Apache Tika's content detection, extraction and language detection capabilities.
        It manages JVM initialization and Tika configuration including custom parsers, detectors and MIME types.

        Args:
            lazy_load: Whether to defer loading language detection models until first use. Defaults to True.
                Setting to False loads models immediately but increases startup time.
            custom_parsers: Custom parsers to add to the Tika pipeline. Can be either a list of Parser instances
                or a callable that returns such a list. Defaults to None.
            custom_detectors: Custom detectors to add to the Tika pipeline. Can be either a list of Detector instances
                or a callable that returns such a list. Defaults to None.
            custom_mime_types: Additional MIME types to register with Tika. Must be in format "type/subtype". Defaults to None.
                Required when adding custom parsers/detectors that handle new MIME types.
            extra_jars: Additional JAR files to add to the JVM classpath. Useful for custom parsers/detectors. Defaults to None.
            tika_jar_override: Path to custom Tika JAR file to use instead of bundled version. Defaults to None.

        Raises:
            ValueError: If a custom MIME type is malformed (incorrect format).
            FileNotFoundError: If specified JAR files don't exist.

        Examples:
            Basic usage:
            >>> from tikara import Tika
            >>> tika = Tika()
            >>> mime_type = tika.detect_mime_type("document.pdf")
            >>> content, metadata = tika.parse("document.pdf")

            With custom parser:
            >>> from custom_parser import MarkdownParser
            >>> tika = Tika(
            ...     custom_parsers=[MarkdownParser()],
            ...     custom_mime_types=["text/markdown"]
            ... )

            With custom detector:
            >>> from custom_detector import MarkdownDetector
            >>> tika = Tika(
            ...     custom_detectors=[MarkdownDetector()],
            ...     custom_mime_types=["text/markdown"]
            ... )

        Notes:
            - Custom parsers and detectors must implement the respective Java interfaces from Apache Tika.
                See examples/custom_parser.ipynb and examples/custom_detector.ipynb for implementation details.
            - The JVM is initialized on first instantiation. Subsequent instances reuse the same JVM.
            - Custom MIME types must be registered when adding custom parsers/detectors for new formats.
            - Language detection models are loaded lazily by default to improve startup time.

        See Also:
            - examples/parsing.ipynb: Examples of content extraction
            - examples/detect_mime_type.ipynb: Examples of MIME type detection
            - examples/detect_language.ipynb: Examples of language detection
            - examples/custom_parser.ipynb: Custom parser implementation
            - examples/custom_detector.ipynb: Custom detector implementation
        """  # noqa: E501

        initialize_jvm(tika_jar_override=tika_jar_override, extra_jars=extra_jars)

        custom_detectors = custom_detectors() if callable(custom_detectors) else custom_detectors or []
        custom_parsers = custom_parsers() if callable(custom_parsers) else custom_parsers or []
        custom_mime_types = custom_mime_types or []

        from java.util import ArrayList as JArrayList
        from org.apache.tika import Tika as JTika
        from org.apache.tika.config import TikaConfig as JTikaConfig
        from org.apache.tika.detect import CompositeDetector, DefaultDetector
        from org.apache.tika.language.detect import LanguageDetector
        from org.apache.tika.mime import MediaType
        from org.apache.tika.parser import AutoDetectParser, DefaultParser

        self._j_tika_config = JTikaConfig.getDefaultConfig()
        self._media_type_registry = self._j_tika_config.getMediaTypeRegistry()

        # if user has custom mime types, add them to the media type registry and validate them
        for custom_mime_type in custom_mime_types:
            try:
                root_type, sub_type = custom_mime_type.split("/")
                self._media_type_registry.addType(MediaType(root_type, sub_type))
            except ValueError:
                msg = f"Invalid custom MIME type: {custom_mime_type}. Type must be in the form 'type/subtype', like 'text/plain'."  # noqa: E501
                raise ValueError(msg) from None

        # important that default detector is last in the list so that custom detectors are checked first
        self._detector: Detector = (
            DefaultDetector()
            if not custom_detectors
            else CompositeDetector(self._media_type_registry, JArrayList([*custom_detectors, DefaultDetector()]))
        )

        self._parser = AutoDetectParser(self._detector, DefaultParser(), *custom_parsers)
        self._tika = JTika(self._detector, self._parser)
        self._language_detector = LanguageDetector.getDefaultLanguageDetector()
        self._models_loaded = False

        if not lazy_load:
            self._ensure_language_models_loaded()

    #
    # MimeType detection
    #
    def detect_mime_type(self, obj: TikaInputType) -> str:
        """Detect the MIME type of a file, bytes, or stream.

        Uses Apache Tika's MIME type detection capabilities which combine file extension examination,
        magic bytes analysis, and content inspection. For best results when using streams/bytes,
        provide content from the beginning of the file since magic byte detection examines file headers.

        Args:
            obj: Input to detect MIME type for. Can be:
                - Path or str: Filesystem path
                - bytes: Raw content bytes
                - BinaryIO: File-like object in binary mode

        Returns:
            str: Detected MIME type in format "type/subtype" (e.g. "application/pdf")

        Raises:
            TypeError: If input type is not supported
            FileNotFoundError: If input file path does not exist
            ValueError: If detection fails

        Examples:
            Path input:
            >>> tika = Tika()
            >>> tika.detect_mime_type("document.pdf")
            'application/pdf'

            Bytes input:
            >>> with open("document.pdf", "rb") as f:
            ...     tika.detect_mime_type(f.read())
            'application/pdf'

            Stream input:
            >>> from io import BytesIO
            >>> bio = BytesIO(b"<html><body>Hello</body></html>")
            >>> tika.detect_mime_type(bio)
            'text/html'

        Notes:
            - Supports all >1600 MIME types recognized by Apache Tika
            - Custom MIME types can be added via custom detectors
            - For reliable detection, provide at least 1KB of content when using bytes/streams
            - Detection order: custom detectors -> default Tika detectors

        See Also:
            - examples/detect_mime_type.ipynb: More detection examples
            - examples/custom_detector.ipynb: Adding custom MIME type detection
        """

        from java.io import ByteArrayInputStream, InputStream
        from java.nio.file import Path as JPath

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
        """Detect the natural language of text content using Apache Tika's language detection.

        Uses statistical language detection models to identify the most likely language. Higher confidence
        and raw scores indicate more reliable detection. For best results, provide at least 50 characters of text.

        Args:
            content: Text content to analyze. Should be plain text, not markup/code.

        Returns:
            TikaraDetectLanguageResult with fields:
                language: ISO 639-1 language code (e.g. "en" for English)
                confidence: Qualitative confidence level (HIGH/MEDIUM/LOW/NONE)
                raw_score: Numeric confidence score between 0 and 1

        Raises:
            ValueError: If content is empty
            RuntimeError: If language detection fails

        Examples:
            High confidence detection:
            >>> tika = Tika()
            >>> result = tika.detect_language("The quick brown fox jumps over the lazy dog")
            >>> result.language
            'en'
            >>> result.confidence
            LanguageConfidence.HIGH
            >>> result.raw_score
            0.999

            Lower confidence example:
            >>> result = tika.detect_language("123")
            >>> result.confidence
            LanguageConfidence.LOW

            Other languages:
            >>> tika.detect_language("El rápido zorro marrón salta sobre el perro perezoso").language
            'es'

        Notes:
            - Models are loaded lazily on first use unless lazy_load=False in constructor
            - Supports ~70 languages including all major European and Asian languages
            - Short or ambiguous content may result in lower confidence scores
            - Language models are memory-intensive; loaded models persist until JVM shutdown

        See Also:
            - examples/detect_language.ipynb: Additional language detection examples
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
        """Extract embedded documents from a container document recursively.

        Extracts and saves embedded documents (e.g. images in PDFs, files in Office documents) to disk.
        Can recursively extract from nested containers up to specified depth.

        Args:
            obj: Input container document to extract from. Can be:
                - Path or str: Filesystem path
                - bytes: Raw content bytes
                - BinaryIO: File-like object in binary mode
            output_dir: Directory to save extracted documents to. Created if doesn't exist.
            max_depth: Maximum recursion depth for nested containers. Default 1 extracts only
                top-level embedded docs.
            input_file_name: Original filename if obj is bytes/stream. Helps with metadata
                extraction.
            content_type: MIME type of input if known. Helps with metadata extraction.

        Returns:
            List[TikaraUnpackedItem], each containing:
                file_path: Path where extracted doc was saved
                metadata: Dict of metadata about extracted doc

        Raises:
            FileNotFoundError: If input file path doesn't exist
            ValueError: If input type not supported
            RuntimeError: If extraction fails

        Examples:
            Basic extraction:
            >>> tika = Tika()
            >>> items = tika.unpack("presentation.pptx", Path("extracted/"))
            >>> for item in items:
            ...     print(f"Found {item.metadata['Content-Type']} at {item.file_path}")
            Found image/png at extracted/image1.png
            Found application/pdf at extracted/embedded.pdf

            Recursive extraction:
            >>> tika.unpack("container.docx", Path("out/"), max_depth=3)
            [TikaraUnpackedItem(file_path='out/image1.emf', metadata={...}),
                TikaraUnpackedItem(file_path='out/report.pdf', metadata={...}),
                TikaraUnpackedItem(file_path='out/report/chart.png', metadata={...})]

        Notes:
            - Creates output_dir if it doesn't exist
            - Handles nested containers (ZIP, PDF, Office docs etc)
            - Extracts images, attachments, embedded files
            - Returns paths are relative to output_dir
            - Metadata includes content type, relations, properties
            - Extraction depth measured from input document
            - For streams/bytes, provide filename/type if possible

        See Also:
            - examples/unpack.ipynb: Additional extraction examples
            - RecursiveEmbeddedDocumentExtractor: Core extraction logic
        """
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        from org.apache.tika.extractor import EmbeddedDocumentExtractor
        from org.apache.tika.parser import ParseContext, Parser
        from org.xml.sax import ContentHandler
        from org.xml.sax.helpers import DefaultHandler

        metadata = _get_metadata(obj=obj, input_file_name=input_file_name, content_type=content_type)

        ch = DefaultHandler()
        pc = ParseContext()
        pc.set(Parser, self._parser)
        pc.set(ContentHandler, ch)
        extractor = RecursiveEmbeddedDocumentExtractor.create(
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
        """Extract content and metadata from a document, returning as a string.

        Default parsing mode that returns content as a string. Best for normal use cases
        where you want to process the extracted text in memory.

        Args:
            obj: Input document (path, bytes, or stream)
            output_format: "txt" for plain text or "xhtml" for structured format (default)
            input_file_name: Original filename if using bytes/stream
            content_type: MIME type if known

        Returns:
            tuple: (extracted_text: str, metadata: dict)

        Example:
            >>> text, meta = tika.parse("document.pdf", output_format="txt")
            >>> print(text[:100])  # First 100 chars
        """
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
        """Extract content and metadata from a document, saving content to a file.

        Saves extracted content to specified file path instead of returning as string.
        Useful for large documents to avoid loading entire content into memory.

        Args:
            obj: Input document (path, bytes, or stream)
            output_file: Path to save extracted content to
            output_format: "txt" for plain text or "xhtml" for structured format (default)
            input_file_name: Original filename if using bytes/stream
            content_type: MIME type if known

        Returns:
            tuple: (output_file_path: Path, metadata: dict)

        Example:
            >>> path, meta = tika.parse("large.pdf", output_file="text.txt")
            >>> print(f"Saved to {path}")
        """
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
        """Extract content and metadata from a document, returning content as a stream.

        Returns content as a binary stream for efficient processing of large documents.
        Stream can be read incrementally without loading entire content into memory.

        Args:
            obj: Input document (path, bytes, or stream)
            output_stream: Must be True to use stream output
            output_format: "txt" for plain text or "xhtml" for structured format (default)
            input_file_name: Original filename if using bytes/stream
            content_type: MIME type if known

        Returns:
            tuple: (content_stream: BinaryIO, metadata: dict)

        Example:
            >>> stream, meta = tika.parse("huge.pdf", output_stream=True)
            >>> for chunk in stream:
            ...     process_chunk(chunk)
        """
        ...

    def _validate_and_prepare_output_file(
        self,
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
        """Extract text content and metadata from documents.

        Uses Apache Tika's parsing capabilities to extract plain text or structured content
        from documents, along with metadata. Supports multiple input and output formats.

        Args:
            obj: Input to parse. Can be:
                - Path or str: Filesystem path
                - bytes: Raw content bytes
                - BinaryIO: File-like object in binary mode
            output_stream: Whether to return content as a stream instead of string
            output_format: Format for extracted text:
                - "txt": Plain text without markup
                - "xhtml": Structured XML with text formatting (default)
            output_file: Save content to this path instead of returning it
            input_file_name: Original filename if obj is bytes/stream
            content_type: MIME type of input if known

        Returns:
            Tuple containing:
            - Content (type depends on output mode):
                - String if no output_file/output_stream
                - Path if output_file specified
                - BinaryIO if output_stream=True
            - Dict of metadata about the document

        Raises:
            ValueError: If output_file needed but not provided
            FileNotFoundError: If input file doesn't exist
            TypeError: If input type not supported

        Examples:
            Basic text extraction:
            >>> tika = Tika()
            >>> content, meta = tika.parse("report.pdf")
            >>> print(f"Title: {meta.get('title')}")
            >>> print(content[:100])  # First 100 chars

            Stream output:
            >>> content, meta = tika.parse(
            ...     "large.pdf",
            ...     output_stream=True,
            ...     output_format="txt"
            ... )
            >>> for line in content:
            ...     process(line)

            Save to file:
            >>> path, meta = tika.parse(
            ...     "input.docx",
            ...     output_file="extracted.txt",
            ...     output_format="txt"
            ... )

            Parse bytes with hints:
            >>> with open("doc.pdf", "rb") as f:
            ...     content, meta = tika.parse(
            ...         f.read(),
            ...         input_file_name="doc.pdf",
            ...         content_type="application/pdf"
            ...     )

        Notes:
            - "xhtml" format preserves document structure
            - "txt" format gives clean plain text
            - Handles >1600 file formats
            - More accurate with filename/type hints
            - Streams good for large files
            - Metadata includes standard Dublin Core fields

        See Also:
            - examples/parsing.ipynb: More parsing examples
        """

        output_mode: Literal["string", "file", "stream"]
        if output_stream:
            output_mode = "stream"
        elif output_file:
            output_mode = "file"
        else:
            output_mode = "string"

        output_file = self._validate_and_prepare_output_file(output_file=output_file, output_format=output_format)
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
                    return _handle_file_output(
                        parser=self._parser,
                        output_file=output_file,
                        input_stream=input_stream,
                        metadata=metadata,
                        output_format=output_format,
                    )
                case "stream":
                    return _handle_stream_output(
                        parser=self._parser,
                        input_stream=input_stream,
                        metadata=metadata,
                        output_format=output_format,
                    )
                case "string":
                    return _handle_string_output(
                        parser=self._parser,
                        input_stream=input_stream,
                        metadata=metadata,
                        output_format=output_format,
                    )
                case _:
                    msg = f"Unsupported mode: {output_mode}"
                    raise ValueError(msg)
