import os
from collections.abc import Generator, Iterable
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from io import BufferedIOBase, UnsupportedOperation
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, TypeGuard, cast, override

import jpype
import jpype.imports
from jpype.types import JArray, JChar, JString

if TYPE_CHECKING:
    from java.io import (
        ByteArrayOutputStream,
        FileOutputStream,
        InputStream,
        PipedInputStream,
        Reader,
    )

#
# JVM utilities
#
TIKA_VERSION = "3.0.0"


def get_jars() -> list[Path]:
    """Get path to bundled Tika JAR file(s).

    Args:
        tika_version (str): The version of Tika to use.

    Returns:
        list[Path]: The list of paths to the Tika JAR file(s) to be included in the JVM classpath.
    """
    if custom_tika_jar := os.environ.get("TIKA_JAR_PATH", None):
        path = Path(custom_tika_jar)
        if not path.exists():
            msg = f"Custom Tika JAR file not found at: {path}"
            raise FileNotFoundError(msg)

        return [path]

    from importlib.resources import files

    tikara_path = Path(str(files("tikara")))
    packages: list[str] = ["app"]

    return [Path(tikara_path, f"jars/tika-{package}-{TIKA_VERSION}.jar") for package in packages]


def initialize_jvm(tika_jar_override: Path | None = None, extra_jars: list[Path] | None = None) -> None:
    """
    Tries to start the JVM with the Tika JAR file(s) in the classpath.
    If the JVM is already started, checks if the Tika JAR file(s) are in the classpath.
    """
    custom_jvm_args = os.environ.get("TIKA_JVM_ARGS", "")

    classpath: list[Path] = get_jars()
    if tika_jar_override:
        if not tika_jar_override.exists():
            msg = f"Custom Tika JAR file not found at: {tika_jar_override}"
            raise FileNotFoundError(msg)
        classpath = [tika_jar_override]
    if extra_jars:
        for jar in extra_jars:
            if not jar.exists():
                msg = f"Extra JAR file not found at: {jar}"
                raise FileNotFoundError(msg)
            classpath.append(jar)

    if not jpype.isJVMStarted():
        jpype.startJVM(custom_jvm_args, classpath=classpath)
        return

    existing_classpath = str(jpype.java.lang.System.getProperty("java.class.path"))

    if "tika" not in existing_classpath.casefold():
        msg = "JVM was already started, but Tika JAR file was not found in the classpath."
        raise RuntimeError(msg)


#
# Java I/O utilities
#
class _JavaReaderWrapper(BinaryIO):
    """Wrapper for Java Reader to make it compatible with Python I/O streams."""

    def __init__(self, java_reader: "Reader", buffer_size: int = 8192) -> None:
        super().__init__()
        from java.io import BufferedReader

        if not isinstance(java_reader, BufferedReader):
            java_reader = BufferedReader(java_reader)

        self._reader = java_reader
        self._buffer_size = buffer_size
        self._buffer = b""
        self._closed = False

    @override
    def readable(self) -> bool:
        return self._reader.ready()

    @override
    def read(self, size: int | None = None) -> bytes:
        size = -1 if size is None else size

        if size == 0:
            return b""

        # If we want all remaining data

        if size < 0:
            chunks: list[bytes] = [self._buffer]
            while True:
                char_buffer = JArray(JChar)(self._buffer_size)  # type: ignore  # noqa: PGH003
                read_count = self._reader.read(char_buffer)
                if read_count == -1:
                    break
                java_str = JString(char_buffer, 0, read_count)  # Create a proper Java String
                python_str = str(java_str)  # This properly handles surrogate pairs
                chunks.append(python_str.encode("utf-8"))
            self._buffer = b""
            return b"".join(chunks)

        # If we have enough in buffer, return from there
        if len(self._buffer) >= size:
            data = self._buffer[:size]
            self._buffer = self._buffer[size:]
            return data

        # Need to read more
        char_buffer = JArray(JChar)(self._buffer_size)  # type: ignore  # noqa: PGH003
        read_count = self._reader.read(char_buffer)
        if read_count == -1:
            # EOF - return whatever is left in buffer
            data = self._buffer
            self._buffer = b""
            return data

        self._buffer += "".join(char_buffer[:read_count]).encode("utf-8")
        return self.read(size)  # Recursively try again with new data

    @override
    def close(self) -> None:
        if not self._closed:
            self._reader.close()
            self._closed = True

    @property
    @override
    def closed(self) -> bool:
        return self._closed

    @override
    def seekable(self) -> bool:
        return False

    @override
    def seek(self, offset: int, whence: int = 0) -> int:
        msg = "Reader does not support seek"
        raise UnsupportedOperation(msg)

    @override
    def writable(self) -> bool:
        return False

    @override
    def readline(self, size: int | None = -1) -> bytes:
        java_str = self._reader.readLine()
        if not java_str:
            return b""
        return str(java_str + "\n").encode("utf-8")

    @override
    def readlines(self, hint: int | None = -1) -> list[bytes]:
        lines = []
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
        return lines

    @override
    def write(self, s: Any) -> int:
        msg = "Reader is not writable"
        raise UnsupportedOperation(msg)

    @override
    def flush(self) -> None:
        pass

    @override
    def __enter__(self) -> "_JavaReaderWrapper":
        return self

    @override
    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:  # noqa: PYI036
        self.close()

    @override
    def writelines(self, lines: Iterable[Any]) -> None:
        msg = "Reader is not writable"
        raise UnsupportedOperation(msg)


def wrap_python_stream(python_stream: BinaryIO) -> "PipedInputStream":
    from java.io import PipedInputStream, PipedOutputStream

    input_stream = PipedInputStream(8192)
    output_stream = PipedOutputStream(input_stream)
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tika-pipe")

    def pipe_data() -> None:
        with output_stream:
            while chunk := python_stream.read(8192):
                output_stream.write(bytearray(chunk))

    executor.submit(pipe_data)
    return input_stream


def read_to_string(source: "Reader | ByteArrayOutputStream") -> str:
    """Read content into a Python string.

    Args:
        source: Either a Java Reader or ByteArrayOutputStream
    """
    from java.io import ByteArrayOutputStream

    if isinstance(source, ByteArrayOutputStream):
        return str(JString(source.toString("UTF-8")))

    # Existing Reader logic
    from java.lang import String

    char_buffer = jpype.JArray(jpype.JChar)(8192)  # type: ignore  # noqa: PGH003
    result = []
    while True:
        read_count = source.read(char_buffer)
        if read_count == -1:
            break
        python_str = str(String(char_buffer, 0, read_count))
        python_str = python_str.encode("utf-16", "surrogatepass").decode("utf-16")
        result.append(python_str)
    return "".join(result)


def stream_to_file(source: "Reader | ByteArrayOutputStream", output_file: Path) -> Path:
    """Stream the contents to a file.

    Args:
        source: Either a Java Reader or ByteArrayOutputStream to read from.
        output_file: The file to write the contents to. The file will be overwritten.

    Returns:
        Path: The path to the output file.
    """
    from java.io import ByteArrayOutputStream

    if not output_file.parent.exists():
        output_file.parent.mkdir(parents=True)

    with output_file.open("w", encoding="utf-8") as f:
        if isinstance(source, ByteArrayOutputStream):
            f.write(str(JString(source.toString("UTF-8"))))
            return output_file

        # Existing Reader logic
        from java.lang import String

        while True:
            char_buffer = jpype.JArray(jpype.JChar)(8192)  # type: ignore  # noqa: PGH003
            read_count = source.read(char_buffer)
            if read_count == -1:
                break
            java_str = String(char_buffer, 0, read_count)
            f.write(str(java_str))
    return output_file


def input_stream_as_binary_stream(java_input_stream: "InputStream") -> BinaryIO:
    """Convert a Java InputStream to a Python binary stream.

    Args:
        java_input_stream (InputStream): The Java InputStream to convert.

    Returns:
        BinaryIO: The Python binary stream that reads from the Java InputStream.
    """
    from java.io import InputStreamReader

    reader = InputStreamReader(java_input_stream)
    return _JavaReaderWrapper(reader)


def reader_as_binary_stream(source: "Reader | ByteArrayOutputStream") -> BinaryIO:
    """Convert a Java Reader or ByteArrayOutputStream to a Python binary stream.

    Args:
        source: Either a Java Reader or ByteArrayOutputStream to convert.

    Returns:
        BinaryIO: The Python binary stream that reads from the source.
    """
    from java.io import ByteArrayOutputStream

    if isinstance(source, ByteArrayOutputStream):
        return _JavaReaderWrapper(output_stream_to_reader(source))
    return _JavaReaderWrapper(source)


def is_binary_io(obj: Any) -> TypeGuard[BinaryIO]:  # noqa: ANN401
    return isinstance(obj, BufferedIOBase)


def output_stream_to_reader(java_output_stream: "ByteArrayOutputStream") -> "Reader":
    """Convert a Java ByteArrayOutputStream to a Java Reader.

    Args:
        java_output_stream (ByteArrayOutputStream): The Java output stream containing data

    Returns:
        Reader: A Java Reader that can read the output stream's contents
    """
    from java.io import ByteArrayInputStream, InputStreamReader

    input_stream = ByteArrayInputStream(java_output_stream.toByteArray())  # type: ignore  # noqa: PGH003
    return InputStreamReader(input_stream)


@contextmanager
def file_output_stream(file_path: Path | str, *, append: bool = False) -> Generator["FileOutputStream", None, None]:
    """Wraps a file path as a FileOutputStream.

    Args:
        file_path (Path): The file path to wrap.
        append (bool): Whether to append to the file. Defaults to False.

    Yields:
        FileOutputStream: The wrapped file output stream.
    """
    from java.io import FileOutputStream

    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True)

    if not file_path.exists():
        file_path.touch(exist_ok=True)

    with FileOutputStream(str(file_path), append) as fos:
        yield cast(FileOutputStream, fos)
