from collections.abc import Generator
from pathlib import Path

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from tikara.java_util import initialize_jvm
from tikara.tika import Tika


@pytest.fixture(autouse=True)
def jvm() -> None:
    initialize_jvm()


@pytest.fixture
def tika() -> Tika:
    return Tika()


@pytest.fixture
def demo_docx() -> Path:
    """A word doc with tables, headers, footers, and images."""
    path = Path("./test/data/demo.docx")
    assert path.exists()
    return path


@pytest.fixture
def test_pdf_child_attachments() -> Path:
    """A PDF with child attachments."""
    path = Path("./test/data/testPDF_childAttachments.pdf")
    assert path.exists()
    return path


@pytest.fixture
def basic_txt() -> Path:
    """Simple text file with the contents 'Hello, world!'."""
    path = Path("./test/data/hello_world.txt")
    assert path.exists()
    return path


@pytest.fixture
def basic_html(tmp_path: Path) -> Path:
    html_path = tmp_path / "sample.html"
    html_path.write_text("<html><body>Sample HTML</body></html>")
    return html_path


@pytest.fixture
def test_recursive_embedded_docx() -> Path:
    """A word doc with multiple levels of embedded files."""
    path = Path("./test/data/test_recursive_embedded.docx")
    assert path.exists()
    return path


@pytest.fixture(scope="module")
def tika_container() -> Generator[DockerContainer, None, None]:
    """Create a Tika instance using the full Tika server."""
    tika_container = DockerContainer("apache/tika:latest-full").with_exposed_ports(9998)
    tika_container.start()
    # Wait for Tika server to be ready
    wait_for_logs(tika_container, "Started Apache Tika server")

    yield tika_container

    tika_container.stop()
