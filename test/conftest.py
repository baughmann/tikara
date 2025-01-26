from collections.abc import Generator
from pathlib import Path

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from tikara.core import Tika
from tikara.util.java import initialize_jvm


@pytest.fixture(autouse=True)
def jvm() -> None:
    initialize_jvm()


@pytest.fixture
def readme() -> Path:
    path = Path("./README.md")
    assert path.exists()
    return path


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="session")
def tika_container() -> Generator[DockerContainer, None, None]:
    """Create a Tika instance using the full Tika server."""
    tika_container = DockerContainer("apache/tika:latest-full").with_exposed_ports(9998)
    tika_container.start()
    # Wait for Tika server to be ready
    wait_for_logs(tika_container, "Started Apache Tika server")

    yield tika_container

    tika_container.stop()


ALL_VALID_DOCS: list[Path] = [
    Path("./test/data/demo.docx"),
    Path("./test/data/testPDF_childAttachments.pdf"),
    Path("./test/data/hello_world.txt"),
    Path("./test/data/test_recursive_embedded.docx"),
    Path("./test/data/2023-half-year-analyses-by-segment.xlsx"),
    Path("./test/data/CantinaBand3.wav"),
    Path("./test/data/category-level.docx"),
    Path("./test/data/coffee.xls"),
    Path("./test/data/contains-pictures.docx"),
    Path("./test/data/docx-shapes.docx"),
    Path("./test/data/docx-tables.docx"),
    Path("./test/data/duplicate-paragraphs.docx"),
    Path("./test/data/emoji.xlsx"),
    Path("./test/data/failure-after-repair.pdf"),
    Path("./test/data/fake-email.eml"),
    Path("./test/data/fake-email-multiple-attachments.msg"),
    Path("./test/data/fake-email-with-cc-and-bcc.msg"),
    Path("./test/data/korean-text-with-tables.pdf"),
    Path("./test/data/README.md"),
    Path("./test/data/README.org"),
    Path("./test/data/science-exploration-369p.pptx"),
    Path("./test/data/simple.epub"),
    Path("./test/data/test.zip"),
]

ALL_INVALID_DOCS: list[Path] = [
    Path("./test/data/bad_xml.xml"),
]

ALL_DOCS: list[Path] = ALL_VALID_DOCS + ALL_INVALID_DOCS
