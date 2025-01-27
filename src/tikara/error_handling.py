"""Collection of custom exceptions for Tikara and error handling utils."""

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import ParamSpec, TypeVar

from jpype.types import JException

P = ParamSpec("P")
R = TypeVar("R")


class TikaError(Exception):
    """Base class for all exceptions raised by Tikara."""


class TikaMimeTypeError(TikaError):
    """Raised when the mimetype is invalid."""

    @classmethod
    def _from_mimetype(cls, mimetype: str) -> "TikaMimeTypeError":
        """Create a new instance from a mimetype."""
        msg = f"Invalid custom MIME type: {mimetype}. Type must be in the form 'type/subtype', like 'text/plain'."
        return cls(msg)


class TikaInputArgumentsError(TikaError):
    """Raised when the input parameters to a method is invalid."""


class TikaInputTypeError(TikaInputArgumentsError):
    """Raised when the input obj type is invalid."""

    @classmethod
    def _from_input_type(cls, input_type: type) -> "TikaInputArgumentsError":
        """Create a new instance from an input type."""
        return cls(f"Invalid input type: {input_type}")


class TikaInputFileNotFoundError(TikaInputArgumentsError):
    """Raised when the input file or directory is not found."""

    @classmethod
    def _from_file(cls, file_path: str | Path) -> "TikaInputFileNotFoundError":
        """Create a new instance from a file path."""
        return cls(f"File not found: {file_path}")


class TikaOutputFormatError(TikaInputArgumentsError):
    """Raised when the output format is invalid."""

    @classmethod
    def _from_output_format(cls, output_format: str) -> "TikaOutputFormatError":
        """Create a new instance from an output format."""
        return cls(f"Invalid output format: {output_format}")


class TikaOutputModeError(TikaInputArgumentsError):
    """Raised when the output mode is invalid."""

    @classmethod
    def _from_output_mode(cls, output_mode: str) -> "TikaOutputModeError":
        """Create a new instance from an output mode."""
        return cls(f"Invalid output mode: {output_mode}")


class TikaInitializationError(TikaError):
    """Raised when the Tika server fails to initialize."""


def wrap_exceptions(func: Callable[P, R]) -> Callable[P, R]:
    """
    Wrap a function to convert Java Tika exceptions to Python TikaError.

    Args:
        func: The function to wrap

    Returns:
        Wrapped function that converts Java exceptions to Python exceptions

    Raises:
        TikaError: When a TikaException occurs
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except JException as e:
            from java.nio.file import NoSuchFileException, NotDirectoryException

            if isinstance(e, NoSuchFileException | NotDirectoryException):
                raise TikaInputFileNotFoundError from e

            raise TikaError(str(e)) from e
        except TikaError:
            raise
        except FileNotFoundError as e:
            raise TikaInputFileNotFoundError(str(e)) from e
        except Exception as e:
            raise TikaError(str(e)) from e

    return wrapper
