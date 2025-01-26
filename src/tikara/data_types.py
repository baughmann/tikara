"""Common data types used in public methods and classes."""

import logging
from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Literal, Self

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from org.apache.tika.metadata import Metadata, Property


TikaParseOutputFormat = Literal["txt", "xhtml"]
TikaInputType = str | Path | bytes | BinaryIO

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TikaUnpackedItem:
    """Represents an unpacked embedded document."""

    metadata: dict[str, str]
    file_path: Path


@unique
class TikaLanguageConfidence(StrEnum):
    """Enum representing the confidence level of a detected language result."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class TikaDetectLanguageResult(BaseModel):
    """Represents the result of a language detection operation."""

    language: str
    confidence: TikaLanguageConfidence
    raw_score: float


def _get_metadata_key_mappings() -> dict[str, list["Property | str"]]:
    from org.apache.tika.metadata import (
        IPTC,
        PDF,
        TIFF,
        XMPDM,
        DublinCore,
        Epub,
        Message,
        Metadata,
        Office,
        OfficeOpenXMLCore,
        OfficeOpenXMLExtended,
        PagedText,
        TikaCoreProperties,
    )

    return {
        # Processing Metadata
        "parse_time_millis": [TikaCoreProperties.PARSE_TIME_MILLIS],
        "encoding": [Metadata.CONTENT_ENCODING, TikaCoreProperties.DETECTED_ENCODING],
        # Document Counts
        "paragraph_count": [Office.PARAGRAPH_COUNT],
        "revision": [OfficeOpenXMLCore.REVISION],
        "word_count": [Office.WORD_COUNT],
        "line_count": [Office.LINE_COUNT],
        "character_count": [Office.CHARACTER_COUNT],
        "character_count_with_spaces": [Office.CHARACTER_COUNT_WITH_SPACES],
        "page_count": [Office.PAGE_COUNT, PagedText.N_PAGES, TIFF.EXIF_PAGE_COUNT],
        "chars_per_page": [PDF.CHARACTERS_PER_PAGE],
        "table_count": [Office.TABLE_COUNT],
        "component_count": ["Number of Components"],
        "image_count": [Office.IMAGE_COUNT],
        "hidden_slides": [OfficeOpenXMLExtended.HIDDEN_SLIDES],
        # Resource Information
        "resource_name": [TikaCoreProperties.RESOURCE_NAME_KEY],
        "embedded_resource_path": [TikaCoreProperties.EMBEDDED_RESOURCE_PATH],
        "embedded_resource_type": [TikaCoreProperties.EMBEDDED_RESOURCE_TYPE],
        "embedded_relationship_id": [TikaCoreProperties.EMBEDDED_RELATIONSHIP_ID],
        "embedded_depth": [TikaCoreProperties.EMBEDDED_DEPTH],
        # Dates
        "created": [DublinCore.CREATED, PDF.DOC_INFO_CREATED],
        "modified": [DublinCore.MODIFIED, PDF.DOC_INFO_MODIFICATION_DATE],
        # Content Information
        "content_type": [Metadata.CONTENT_TYPE],
        "content_type_override": [TikaCoreProperties.CONTENT_TYPE_USER_OVERRIDE],
        "content_length": [Metadata.CONTENT_LENGTH],
        # Document Content Metadata
        "title": [DublinCore.TITLE, PDF.DOC_INFO_TITLE, DublinCore.SUBJECT, PDF.DOC_INFO_SUBJECT],
        "description": [DublinCore.DESCRIPTION],
        "type": [DublinCore.TYPE],
        "keywords": [Office.KEYWORDS, IPTC.KEYWORDS, PDF.DOC_INFO_KEY_WORDS, "meta:keyword"],
        "notes": [OfficeOpenXMLExtended.NOTES],
        # Author Information
        "company": [OfficeOpenXMLExtended.COMPANY],
        "creator": [DublinCore.CREATOR, Office.LAST_AUTHOR, PDF.DOC_INFO_CREATOR, PDF.DOC_INFO_PRODUCER],
        "publisher": [DublinCore.PUBLISHER],
        "contributor": [DublinCore.CONTRIBUTOR],
        # Language
        "language": [DublinCore.LANGUAGE],
        # Application Metadata
        "identifier": [DublinCore.IDENTIFIER],
        "application": [OfficeOpenXMLExtended.APPLICATION, PDF.DOC_INFO_CREATOR_TOOL],
        "application_version": [OfficeOpenXMLExtended.APP_VERSION],
        "producer": [PDF.PRODUCER],
        "version": [PDF.PDF_VERSION, Epub.VERSION],
        "template": [OfficeOpenXMLExtended.TEMPLATE],
        "is_encrypted": [PDF.IS_ENCRYPTED, OfficeOpenXMLExtended.SECURITY_PASSWORD_PROTECTED],
        # Security Metadata
        "security": [
            OfficeOpenXMLExtended.SECURITY_NONE,
            OfficeOpenXMLExtended.SECURITY_PASSWORD_PROTECTED,
            OfficeOpenXMLExtended.SECURITY_READ_ONLY_ENFORCED,
            OfficeOpenXMLExtended.SECURITY_READ_ONLY_RECOMMENDED,
            OfficeOpenXMLExtended.SECURITY_LOCKED_FOR_ANNOTATIONS,
            OfficeOpenXMLExtended.SECURITY_UNKNOWN,
            OfficeOpenXMLExtended.DOC_SECURITY,
            OfficeOpenXMLExtended.DOC_SECURITY_STRING,
        ],
        # Image Metadata
        "height": ["height"],
        "width": ["width"],
        "pixel_aspect_ratio": [XMPDM.VIDEO_PIXEL_ASPECT_RATIO],
        "compression_type": ["Compression CompressionTypeName"],
        "color_space": [XMPDM.VIDEO_COLOR_SPACE],
        # Audio Metadata
        "audio_sample_rate": [XMPDM.AUDIO_SAMPLE_RATE],
        "audio_channels": [XMPDM.AUDIO_CHANNEL_TYPE],
        "audio_bits": ["bits"],
        "audio_sample_type": [XMPDM.AUDIO_SAMPLE_TYPE],
        "audio_encoding": ["encoding"],
        "audio_duration": [XMPDM.DURATION],
        "audio_compression": [XMPDM.AUDIO_COMPRESSOR],
        "file_name": ["File Name"],
        "embed_depth": [TikaCoreProperties.EMBEDDED_DEPTH],
        # Message Information
        "from": [Message.MESSAGE_FROM, Message.MESSAGE_FROM_EMAIL, Message.MESSAGE_FROM_NAME],
        "to": [
            Message.MESSAGE_TO,
            Message.MESSAGE_TO_EMAIL,
            Message.MESSAGE_TO_NAME,
            Message.MESSAGE_TO_DISPLAY_NAME,
            Message.MESSAGE_RECIPIENT_ADDRESS,
        ],
        "cc": [
            Message.MESSAGE_CC,
            Message.MESSAGE_CC_EMAIL,
            Message.MESSAGE_CC_NAME,
            Message.MESSAGE_CC_DISPLAY_NAME,
        ],
        "bcc": [
            Message.MESSAGE_BCC,
            Message.MESSAGE_BCC_EMAIL,
            Message.MESSAGE_BCC_NAME,
            Message.MESSAGE_BCC_DISPLAY_NAME,
        ],
        "multipart_subtypes": [Message.MULTIPART_SUBTYPE],
        "multipart_boundary": [Message.MULTIPART_BOUNDARY],
    }


class TikaMetadata(BaseModel):
    """Normalized metadata from Tika document processing with standardized field names."""

    # Processing Metadata
    encoding: str | None = Field(default=None, description="The detected encoding of the document")

    # Document Counts
    paragraph_count: int | None = Field(default=None, description="The number of paragraphs in the document")
    revision: str | None = Field(default=None, description="The revision number of the document")
    word_count: int | None = Field(default=None, description="The number of words in the document")
    line_count: int | None = Field(default=None, description="The number of lines in the document")
    character_count: int | None = Field(
        default=None, description="The number of characters in the document excluding spaces"
    )
    character_count_with_spaces: int | None = Field(
        default=None, description="The number of characters in the document including spaces"
    )
    page_count: int | None = Field(default=None, description="The number of pages in the document")
    chars_per_page: list[int] | int | None = Field(
        default=None,
        description="The number of characters per page in the document. If multiple pages, list of values.",
    )
    table_count: str | None = Field(
        default=None,
        description="The number of tables in the document. This is a string because it can really be anything.",
    )
    component_count: int | None = Field(default=None, description="The number of components in the document")
    image_count: int | None = Field(default=None, description="The number of images in the document")
    hidden_slides: str | None = Field(default=None, description="The number of hidden slides in the document")

    # Resource Information
    resource_name: str | None = Field(
        default=None, description="The name of the resource. Most often just the path to the input file."
    )
    resource_path: str | None = Field(default=None, description="The path to the resource in the document if embedded.")
    embedded_resource_type: str | None = Field(default=None, description="The type of the resource if embedded.")
    embedded_relationship_id: str | None = Field(
        default=None, description="The relationship ID of the embedded resource."
    )
    embedded_depth: int | None = Field(default=None, description="The depth of the embedded resource.")

    # Dates
    created: str | None = Field(default=None, description="The date the document was created")
    modified: str | None = Field(default=None, description="The date the document was last modified")

    # Content Information
    content_type: str | None = Field(default=None, description="The detected content type of the document")
    content_type_override: str | None = Field(
        default=None, description="The content type of the document as overridden by the user"
    )
    content_length: int | None = Field(default=None, description="The length of the document content in bytes")

    # Document Content Metadata
    title: str | None = Field(default=None, description="The title or subject of the document")
    description: str | None = Field(default=None, description="The description of the document")
    type: str | None = Field(default=None, description="The type of the document")
    keywords: str | list[str] | None = Field(default=None, description="The keywords of the document")

    # Author Information
    company: str | None = Field(default=None, description="The company that created the document")
    creator: str | None = Field(default=None, description="The name of the person that created the document")
    publisher: str | None = Field(default=None, description="The publisher of the document")
    contributor: str | None = Field(default=None, description="A list of contributors to the document")

    # Language
    language: str | None = Field(default=None, description="The detected language of the document")

    # Application Metadata
    identifier: str | None = Field(default=None, description="The identifier of the document, Unknown.")
    application: str | None = Field(default=None, description="The application that created the document")
    application_version: str | None = Field(default=None, description="The version of the application")
    producer: str | None = Field(default=None, description="The producer of the document. Unknown.")
    version: str | None = Field(default=None, description="The version of the document")
    template: str | None = Field(
        default=None, description="The template use to create the document. Most common in office docs."
    )
    # Security Metadata
    security: str | None = Field(default=None, description="The security status of the document")
    is_encrypted: bool | str | None = Field(default=None, description="Whether the document is encrypted")

    # Image Metadata
    height: int | None = Field(default=None, description="The height of the image in pixels")
    width: int | None = Field(default=None, description="The width of the image in pixels")
    pixel_aspect_ratio: float | None = Field(default=None, description="The pixel aspect ratio of the image")
    compression_type: str | None = Field(default=None, description="The compression type of the image")
    color_space: str | None = Field(default=None, description="The color space of the image")

    # Audio Metadata
    audio_sample_rate: int | None = Field(default=None, description="The audio sample rate")
    audio_channels: int | None = Field(default=None, description="The number of audio channels")
    audio_bits: int | None = Field(default=None, description="The number of bits in the audio")
    audio_sample_type: str | None = Field(default=None, description="The audio sample type")
    audio_encoding: str | None = Field(default=None, description="The audio encoding type")
    audio_duration: float | None = Field(default=None, description="The audio duration in seconds")
    audio_compression: str | None = Field(default=None, description="The audio compression type")
    file_name: str | None = Field(default=None, description="The name of the file")

    # Message Information
    from_: str | None = Field(alias="from", default=None, description="The sender of the message")
    to: str | None = Field(default=None, description="The recipient of the message")
    cc: str | None = Field(default=None, description="The carbon copy recipient of the message")
    bcc: str | None = Field(default=None, description="The blind carbon copy recipient of the message")
    multipart_subtypes: str | None = Field(default=None, description="The subtypes of the multipart message")
    multipart_boundary: str | None = Field(default=None, description="The boundary of the multipart message")

    # Raw
    raw_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="The raw metadata from Tika. This often has more data that included in the class properties.",
    )

    @classmethod
    def _from_java_metadata(cls, metadata: "Metadata") -> Self:  # noqa: C901, PLR0912
        from org.apache.tika.metadata import Property

        mappings: dict[str, list[Property | str]] = _get_metadata_key_mappings()
        raw_metadata: dict[str, Any] = cls._metadata_to_dict(metadata)
        data: dict[str, Any] = {"raw_metadata": raw_metadata}

        for field_name, tika_keys in mappings.items():
            for key in tika_keys:
                try:
                    # Handle Property objects vs string keys
                    lookup_key = key.getName() if isinstance(key, Property) else key
                    if lookup_key in raw_metadata:
                        value = raw_metadata[lookup_key]

                        # Handle specific type conversions
                        if field_name in cls.__annotations__:
                            field_type = cls.__annotations__[field_name]
                            if "int" in str(field_type) and value:
                                try:
                                    value = int(value)
                                except (ValueError, TypeError):
                                    continue
                            elif "float" in str(field_type) and value:
                                try:
                                    value = float(value)
                                except (ValueError, TypeError):
                                    continue
                            elif "list[int]" in str(field_type) and value:
                                try:
                                    if isinstance(value, str):
                                        value = [int(x) for x in value.split(",")]
                                    elif isinstance(value, list | tuple):
                                        value = [int(x) for x in value]
                                except (ValueError, TypeError):
                                    continue
                            elif "list[str]" in str(field_type) and value:
                                try:
                                    if isinstance(value, str):
                                        value = value.split(",")
                                        value = [x.strip() for x in value]
                                    elif isinstance(value, list | tuple):
                                        value = [str(x) for x in value]
                                except (ValueError, TypeError):
                                    continue
                            else:
                                value = str(value)

                        data[field_name] = value or None
                        break  # Use first matching value
                except Exception as e:  # noqa: BLE001
                    # don't let one field error stop the rest of the processing
                    logger.warning(f"Error processing field {field_name}: {e}")

        return cls(**data)

    @staticmethod
    def _metadata_to_dict(metadata: "Metadata") -> dict[str, Any]:
        return {str(key): str(metadata.get(key)) for key in metadata.names()}
