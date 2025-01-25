import pytest
import requests
from testcontainers.core.container import DockerContainer

from tikara.tika import LanguageConfidence, Tika

TEST_TEXTS: list[tuple[str, str, LanguageConfidence, float]] = [
    ("en", "The quick brown fox jumps over the lazy dog", LanguageConfidence.HIGH, 0.9),
    (
        "es",
        "El rápido zorro marrón salta sobre el perro perezoso",
        LanguageConfidence.HIGH,
        0.9,
    ),
    ("de", "Der schnelle braune Fuchs springt über den faulen Hund", LanguageConfidence.HIGH, 0.9),
]


@pytest.mark.parametrize(("language", "text", "confidence", "raw_score_min"), TEST_TEXTS)
def test_detect_language_from_str(
    tika: Tika, language: str, text: str, confidence: LanguageConfidence, raw_score_min: float
) -> None:
    """Test language detection from string buffer."""
    result = tika.detect_language(text)
    assert result.language == language
    assert result.confidence == confidence
    assert result.raw_score > raw_score_min


@pytest.fixture
def tika_server_detect_language_request_params(tika_container: DockerContainer) -> tuple[str, dict[str, str]]:
    host_port = tika_container.get_exposed_port(9998)
    container_ip = tika_container.get_container_host_ip()
    url = f"http://{container_ip}:{host_port}/language/stream"

    headers = {"Accept": "text/plain", "Content-Type": "text/plain"}

    return url, headers


@pytest.mark.parametrize(("language", "text", "confidence", "raw_score_min"), TEST_TEXTS)
def test_detect_language_from_str_compare_with_tika_server(
    tika: Tika,
    language: str,
    text: str,
    confidence: LanguageConfidence,
    raw_score_min: float,
    tika_server_detect_language_request_params: tuple[str, dict[str, str]],
) -> None:
    """Test language detection from string buffer as compared to the Tika server."""
    result = tika.detect_language(text)
    assert result.language == language
    assert result.confidence == confidence
    assert result.raw_score > raw_score_min

    url, headers = tika_server_detect_language_request_params
    result_server = requests.put(url, headers=headers, data=text.encode())

    assert result_server.text == language
