import tempfile
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import jpype
import pytest
from jpype import JString

from tikara.core import Tika
from tikara.util.java import (
    TIKA_VERSION,
    _file_output_stream,
    _JavaReaderWrapper,
    _wrap_python_stream,
    output_stream_or_reader_stream_to_file,
    read_to_string,
    reader_as_binary_stream,
)


def test_jvm_classpath() -> None:
    Tika()
    classpath = jpype.java.lang.System.getProperty("java.class.path")
    assert f"tika-app-{TIKA_VERSION}.jar" in classpath


class TestJavaReaderWrapper:
    def test_read_all_at_once(self) -> None:
        from java.io import StringReader

        test_data = "Hello, World!"
        reader = StringReader(test_data)
        stream = _JavaReaderWrapper(reader)

        result = stream.read()
        assert result.decode("utf-8") == test_data

    def test_read_in_chunks(self) -> None:
        from java.io import StringReader

        test_data = "Hello, World!"
        reader = StringReader(test_data)
        stream = _JavaReaderWrapper(reader)

        chunks = []
        while chunk := stream.read(5):
            chunks.append(chunk.decode("utf-8"))

        assert "".join(chunks) == test_data

    def test_read_empty(self) -> None:
        from java.io import StringReader

        reader = StringReader("")
        stream = _JavaReaderWrapper(reader)

        result = stream.read()
        assert result == b""

    def test_read_unicode(self) -> None:
        from java.io import StringReader

        test_data = "Hello, 世界!"
        reader = StringReader(test_data)
        stream = _JavaReaderWrapper(reader)

        result = stream.read()
        assert result.decode("utf-8") == test_data

    def test_read_zero_bytes(self) -> None:
        from java.io import StringReader

        stream = _JavaReaderWrapper(StringReader("Hello, World!"))

        result = stream.read(0)
        assert result == b""

    def test_multiple_reads(self) -> None:
        from java.io import StringReader

        reader = StringReader("Hello, World!")
        stream = _JavaReaderWrapper(reader)

        first = stream.read(5)
        second = stream.read(5)
        third = stream.read()

        assert first.decode("utf-8") == "Hello"
        assert second.decode("utf-8") == ", Wor"
        assert third.decode("utf-8") == "ld!"

    def test_large_data(self) -> None:
        from java.io import StringReader

        test_data = "x" * 100000
        reader = StringReader(test_data)
        stream = _JavaReaderWrapper(reader)

        result = stream.read()
        assert result.decode("utf-8") == test_data

    def test_read_past_eof(self) -> None:
        from java.io import StringReader

        reader = StringReader("Hello")
        stream = _JavaReaderWrapper(reader)

        stream.read()  # Read all data
        result = stream.read()  # Try reading again
        assert result == b""

    def test_small_buffer_size(self) -> None:
        from java.io import StringReader

        reader = StringReader("Hello, World!")
        stream = _JavaReaderWrapper(reader, buffer_size=3)

        result = stream.read()
        assert result.decode("utf-8") == "Hello, World!"

    def test_reader_close(self) -> None:
        from java.io import IOException, StringReader

        reader = StringReader("Hello")
        stream = _JavaReaderWrapper(reader)

        stream.close()

        # The Java Reader should now be closed
        with pytest.raises(IOException):  # jpype will wrap the Java IOException
            reader.read()

    def test_contextmanager_close(self) -> None:
        from java.io import IOException, StringReader

        with _JavaReaderWrapper(StringReader("Hello")) as r:
            pass

        # The Java Reader should now be closed
        with pytest.raises(IOException):
            r.read()

    def test_readline(self) -> None:
        from java.io import StringReader

        test_data = "Line 1\nLine 2\nLine 3"
        reader = StringReader(test_data)
        stream = _JavaReaderWrapper(reader)

        result = stream.readline()
        assert result.decode("utf-8") == "Line 1\n"

        result = stream.readline()
        assert result.decode("utf-8") == "Line 2\n"

        result = stream.readline()
        assert result.decode("utf-8") == "Line 3\n"

        result = stream.readline()
        assert result == b""

    def test_readlines(self) -> None:
        from java.io import StringReader

        test_data = "Line 1\nLine 2\nLine 3"
        reader = StringReader(test_data)
        stream = _JavaReaderWrapper(reader)

        result = stream.readlines()
        assert result == [b"Line 1\n", b"Line 2\n", b"Line 3\n"]


class TestReadToString:
    def test_read_to_string_basic(self) -> None:
        test_data = "Hello, World!"
        from java.io import StringReader

        result = read_to_string(StringReader(test_data))
        assert result == test_data

    def test_read_to_string_empty(self) -> None:
        from java.io import StringReader

        result = read_to_string(StringReader(""))
        assert result == ""

    def test_read_to_string_unicode(self) -> None:
        from java.io import StringReader

        test_data = "Hello, 世界! 🌍"

        result = read_to_string(StringReader(test_data))
        assert result == test_data

    def test_read_to_string_large_data(self) -> None:
        from java.io import StringReader

        test_data = "x" * 100000

        result = read_to_string(StringReader(test_data))
        assert result == test_data

    def test_read_to_string_multiline(self) -> None:
        from java.io import StringReader

        test_data = "Line 1\nLine 2\nLine 3"

        result = read_to_string(StringReader(test_data))
        assert result == test_data


class TestStreamToFile:
    def test_stream_to_file_basic(self) -> None:
        from java.io import StringReader

        test_data = "Hello, World!"

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test.txt"
            result_path = output_stream_or_reader_stream_to_file(StringReader(test_data), output_path)

            assert result_path == output_path
            assert output_path.exists()
            assert output_path.read_text() == test_data

    def test_stream_to_file_empty(self) -> None:
        from java.io import StringReader

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "empty.txt"
            result_path = output_stream_or_reader_stream_to_file(StringReader(""), output_path)

            assert result_path == output_path
            assert output_path.exists()
            assert output_path.read_text() == ""

    def test_stream_to_file_unicode(self) -> None:
        from java.io import StringReader

        test_data = "Hello, 世界! 🌍"

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "unicode.txt"
            result_path = output_stream_or_reader_stream_to_file(StringReader(test_data), output_path)

            assert result_path == output_path
            assert output_path.exists()
            assert output_path.read_text() == test_data

    def test_stream_to_file_large_data(self) -> None:
        from java.io import StringReader

        test_data = "x" * 100000

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "large.txt"
            result_path = output_stream_or_reader_stream_to_file(StringReader(test_data), output_path)

            assert result_path == output_path
            assert output_path.exists()
            assert output_path.read_text() == test_data

    def test_stream_to_file_overwrites_existing(self) -> None:
        from java.io import StringReader

        initial_data = "Initial content"
        test_data = "New content"

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "overwrite.txt"
            output_path.write_text(initial_data)

            result_path = output_stream_or_reader_stream_to_file(StringReader(test_data), output_path)

            assert result_path == output_path
            assert output_path.exists()
            assert output_path.read_text() == test_data

    def test_stream_to_file_invalid_path(self) -> None:
        from java.io import StringReader

        invalid_path = Path("/nonexistent/directory/file.txt")

        with pytest.raises(OSError):  # noqa: PT011
            output_stream_or_reader_stream_to_file(StringReader("test"), invalid_path)


class TestPipeToStream:
    def test_pipe_to_basic(self) -> None:
        from java.io import StringReader

        test_data = "Hello, World!"

        r = reader_as_binary_stream(StringReader(test_data))
        assert isinstance(r, BinaryIO)

        result = r.read()
        assert isinstance(result, bytes)
        assert result.decode("utf-8") == test_data

    def test_pipe_to_read_chunks(self) -> None:
        from java.io import StringReader

        test_data = "Hello, World!"

        r = reader_as_binary_stream(StringReader(test_data))
        chunks = []

        while chunk := r.read(5):
            chunks.append(chunk.decode("utf-8"))

        assert "".join(chunks) == test_data

    def test_pipe_to_empty(self) -> None:
        from java.io import StringReader

        r = reader_as_binary_stream(StringReader(""))
        result = r.read()

        assert result == b""

    def test_pipe_to_unicode(self) -> None:
        from java.io import StringReader

        test_data = "Hello, 世界! 🌍"

        r = reader_as_binary_stream(StringReader(test_data))
        result = r.read()

        assert result.decode("utf-8") == test_data

    def test_pipe_to_large_data(self) -> None:
        from java.io import StringReader

        test_data = "x" * 100000

        r = reader_as_binary_stream(StringReader(test_data))
        result = r.read()

        assert result.decode("utf-8") == test_data

    def test_pipe_to_closed_reader(self) -> None:
        from java.io import IOException, StringReader

        r = reader_as_binary_stream(StringReader("Hello"))

        r.close()

        with pytest.raises(IOException):
            r.read()


class TestWrapPythonStream:
    def test_basic_streaming(self) -> None:
        from java.io import PipedInputStream

        test_data = b"Hello, World!"
        bio = BytesIO(test_data)

        stream = _wrap_python_stream(bio)
        assert isinstance(stream, PipedInputStream)

        # Read individual bytes from Java stream
        result = bytearray()
        while (b := stream.read()) != -1:  # Java streams return -1 at EOF
            result.append(b)

        assert bytes(result) == test_data

    def test_large_data_streaming(self) -> None:
        test_data = b"x" * 100000
        bio = BytesIO(test_data)

        stream = _wrap_python_stream(bio)

        # Read byte-by-byte
        result = bytearray()
        while (b := stream.read()) != -1:
            result.append(b)

        assert bytes(result) == test_data

    def test_empty_stream(self) -> None:
        bio = BytesIO(b"")
        stream = _wrap_python_stream(bio)

        assert stream.read() == -1  # Java streams return -1 at EOF

    def test_binary_data(self) -> None:
        # Include null bytes and other binary data
        test_data = bytes(range(256))
        bio = BytesIO(test_data)

        stream = _wrap_python_stream(bio)

        result = bytearray()
        while (b := stream.read()) != -1:
            result.append(b)

        assert bytes(result) == test_data

    def test_stream_closes_properly(self) -> None:
        from java.io import IOException

        bio = BytesIO(b"test data")
        stream = _wrap_python_stream(bio)

        stream.close()

        # Java stream should be closed
        with pytest.raises(IOException):
            stream.read()

    def test_partial_reads(self) -> None:
        test_data = b"Hello, World!"
        bio = BytesIO(test_data)

        stream = _wrap_python_stream(bio)

        result = bytearray()
        # Read first 5 bytes
        for _ in range(5):
            b = stream.read()
            assert b != -1
            result.append(b)
        assert bytes(result) == b"Hello"

        # Read next 7 bytes
        result.clear()
        for _ in range(7):
            b = stream.read()
            assert b != -1
            result.append(b)
        assert bytes(result) == b", World"

        # Read last byte
        result.clear()
        b = stream.read()
        assert b != -1
        result.append(b)
        assert bytes(result) == b"!"

        # Should be at EOF
        assert stream.read() == -1

    def test_concurrent_access(self) -> None:
        from queue import Queue
        from threading import Thread

        test_data = b"x" * 100000
        bio = BytesIO(test_data)
        stream = _wrap_python_stream(bio)
        results = Queue()

        def reader_thread() -> None:
            try:
                result = bytearray()
                while (b := stream.read()) != -1:
                    result.append(b)
                results.put(bytes(result))
            except Exception as e:  # noqa: BLE001
                results.put(e)

        # Start reader thread
        thread = Thread(target=reader_thread, name="test-reader")
        thread.start()
        thread.join(timeout=5)  # Ensure test doesn't hang

        assert not thread.is_alive(), "Reader thread timed out"
        result = results.get()
        assert isinstance(result, bytes), f"Got exception: {result}"
        assert result == test_data


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_creates_parent_directories(temp_dir: Path) -> None:
    nested_path: Path = temp_dir / "deep" / "nested" / "file.txt"

    with _file_output_stream(nested_path) as fos:
        fos.write(JString("test").getBytes())

    assert nested_path.parent.exists()
    assert nested_path.exists()
    assert nested_path.read_text() == "test"


def test_append_mode(temp_dir: Path) -> None:
    test_file: Path = temp_dir / "test.txt"
    test_str = "test"

    # First write
    with _file_output_stream(test_file) as fos:
        fos.write(JString(test_str).getBytes())

    # Append
    with _file_output_stream(test_file, append=True) as fos:
        fos.write(JString(test_str).getBytes())

    assert test_file.read_text() == f"{test_str}{test_str}"

    # Overwrite
    with _file_output_stream(test_file, append=False) as fos:
        fos.write(JString("new").getBytes())

    assert test_file.read_text() == "new"


def test_str_path_handling(temp_dir: Path) -> None:
    test_file: str = str(temp_dir / "test.txt")
    test_str = "test"

    with _file_output_stream(test_file) as fos:
        fos.write(JString(test_str).getBytes())

    result_path: Path = Path(test_file)
    assert result_path.exists()
    assert result_path.read_text() == test_str


def test_file_stream_handles_binary(temp_dir: Path) -> None:
    test_file: Path = temp_dir / "binary.dat"
    test_bytes: bytes = bytes([0x00, 0xFF, 0x0F, 0xF0])

    with _file_output_stream(test_file) as fos:
        fos.write(test_bytes)

    assert test_file.read_bytes() == test_bytes
