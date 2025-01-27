"""Main package entrypoint for Tikara."""

from tikara.core import Tika
from tikara.data_types import (
    TikaDetectLanguageResult,
    TikaInputType,
    TikaLanguageConfidence,
    TikaMetadata,
    TikaParseOutputFormat,
    TikaUnpackedItem,
    TikaUnpackResult,
)
from tikara.error_handling import TikaError

__all__ = [
    "Tika",
    "TikaDetectLanguageResult",
    "TikaError",
    "TikaInputType",
    "TikaLanguageConfidence",
    "TikaMetadata",
    "TikaParseOutputFormat",
    "TikaUnpackResult",
    "TikaUnpackedItem",
]
