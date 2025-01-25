<img src="https://raw.githubusercontent.com/baughmann/tikara/refs/heads/master/tikara_logo.svg" width="100" alt="Tikara Logo" />

# Tikara

![Coverage](https://img.shields.io/badge/dynamic/xml?url=https://raw.githubusercontent.com/baughmann/tikara/refs/heads/master/coverage.xml&query=/coverage/@line-rate%20*%20100&suffix=%25&color=brightgreen&label=coverage) ![Tests](https://img.shields.io/badge/dynamic/xml?url=https://raw.githubusercontent.com/baughmann/tikara/refs/heads/master/junit.xml&query=/testsuites/testsuite/@tests&label=tests&color=green) ![PyPI](https://img.shields.io/pypi/v/tikara) ![GitHub License](https://img.shields.io/github/license/baughmann/tikara) ![PyPI - Downloads](https://img.shields.io/pypi/dm/tikara) ![GitHub issues](https://img.shields.io/github/issues/baughmann/tikara) ![GitHub pull requests](https://img.shields.io/github/issues-pr/baughmann/tikara) ![GitHub stars](https://img.shields.io/github/stars/baughmann/tikara?style=social)

## 🚀 Overview

Tikara is a modern, type-hinted Python wrapper for Apache Tika, supporting over 1600 file formats for content extraction, metadata analysis, and language detection. It provides direct JNI integration through JPype for optimal performance.

```python
from tikara import Tika

tika = Tika()
content, metadata = tika.parse("document.pdf")
```

## ⚡️ Key Features

- Modern Python 3.12+ with complete type hints
- Direct JVM integration via JPype (no HTTP server required)
- Streaming support for large files
- Recursive document unpacking
- Language detection
- MIME type detection
- Custom parser and detector support
- Comprehensive metadata extraction

## 📦 Supported Formats

🌈 **1682 supported media types and counting!**

[🔍 See the full list →](/SUPPORTED_MIME_TYPES.md)

## 🛠 Installation

```bash
pip install tikara
```

### System Dependencies

#### Required

- Python 3.12+
- Java Development Kit 11+ (OpenJDK recommended)
- If you want to do OCR you will need Tesseract OCR with dependencies:

  ```bash
  # Ubuntu
  apt-get install tesseract-ocr tesseract-ocr-eng imagemagick

  # Language packs (optional)
  apt-get install tesseract-ocr-deu tesseract-ocr-fra tesseract-ocr-ita tesseract-ocr-spa

  # Required paths (if not on system PATH)
  export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata
  export TESSERACT_PATH=/usr/bin/tesseract
  export IMAGEMAGICK_PATH=/usr/bin/convert
  ```

  Note: ImageMagick is required for OCR preprocessing including rotation correction, density adjustment, and color space management.

#### Font Dependencies

```bash
# Ubuntu
apt-get install xfonts-utils fonts-freefont-ttf fonts-liberation ttf-mscorefonts-installer
```

#### Geospatial Support

```bash
# Ubuntu
apt-get install gdal-bin
```

#### Optional Enhancements

- LibreOffice for improved Office file handling
- ImageMagick for advanced image processing
- Additional Tesseract language packs as needed

For more OS dependency information including MSCore fonts setup and additional configuration, see the [official Apache Tika Dockerfile](https://github.com/apache/tika-docker/blob/main/full/Dockerfile).

## 📖 Usage

[Example Jupyter Notebooks](https://github.com/baughmann/tikara/tree/master/examples) 📔

### Basic Content Extraction

```python
from tikara import Tika
from pathlib import Path

tika = Tika()

# Basic string output
content, metadata = tika.parse("document.pdf")

# Stream large files
stream, metadata = tika.parse(
    "large.pdf",
    output_stream=True,
    output_format="txt"
)

# Save to file
output_path, metadata = tika.parse(
    "input.docx",
    output_file=Path("output.txt"),
    output_format="txt"
)
```

### Language Detection

```python
from tikara import Tika

tika = Tika()
result = tika.detect_language("El rápido zorro marrón salta sobre el perro perezoso")
print(f"Language: {result.language}, Confidence: {result.confidence}")
```

### MIME Type Detection

```python
from tikara import Tika

tika = Tika()
mime_type = tika.detect_mime_type("unknown_file")
print(f"Detected type: {mime_type}")
```

### Recursive Document Unpacking

```python
from tikara import Tika
from pathlib import Path

tika = Tika()
results = tika.unpack(
    "container.docx",
    output_dir=Path("extracted"),
    max_depth=3
)

for item in results:
    print(f"Extracted {item.metadata['Content-Type']} to {item.file_path}")
```

## 🔧 Development

### Environment Setup

1. Install Python 3.12+ and JDK 11+
2. Install uv: `pip install uv`
3. Install dependencies: `uv sync`

### Common Tasks

```bash
make ruff        # Format and lint code
make test        # Run test suite
make docs        # Generate documentation
make stubs       # Generate Java stubs
make prepush     # Run all checks (ruff, test, coverage, safety)
```

## 🤔 When to Use Tikara

### Ideal Use Cases

- Python applications needing document processing
- Microservices and containerized environments
- Data processing pipelines ([Ray](https://ray.io), [Dask](https://dask.org), [Prefect](https://prefect.io))
- Applications requiring direct Tika integration without HTTP overhead

### Advanced Usage

For detailed documentation on:

- Custom parser implementation
- Custom detector creation
- MIME type handling
- Custom JAR integration
- Performance optimization

See [ADVANCED.md](ADVANCED.md)

## 🎯 Inspiration

Tikara builds on the shoulders of giants:

- [Apache Tika](https://tika.apache.org/) - The powerful content detection and extraction toolkit
- [tika-python](https://github.com/chrismattmann/tika-python) - The original Python Tika wrapper using HTTP
- [JPype](https://jpype.readthedocs.io/) - The bridge between Python and Java

### Considerations

- Process isolation: Tika crashes will affect the host application
- Memory management: Large documents require careful handling
- JVM startup: Initial overhead for first operation
- Custom implementations: Parser/detector development requires Java interface knowledge

## 📊 Performance Considerations

### Memory Management

- Use streaming for large files
- Monitor JVM heap usage
- Consider process isolation for critical applications

### Optimization Tips

- Reuse Tika instances
- Use appropriate output formats
- Implement custom parsers for specific needs
- Configure JVM parameters for your use case

## 🔐 Security Considerations

- Input validation
- Resource limits
- Secure file handling
- Access control for extracted content
- Careful handling of custom parsers

## 🤝 Contributing

Contributions welcome! The project uses Make for development tasks:

```bash
make prepush     # Run all checks (format, lint, test, coverage, safety)
```

For developing custom parsers/detectors, Java stubs can be generated:

```bash
make stubs       # Generate Java stubs for Apache Tika interfaces
```

Note: Generated stubs are git-ignored but provide IDE support and type hints when implementing custom parsers/detectors.

## Common Problems

- Verify Java installation and JAVA_HOME environment variable
- Ensure Tesseract and required language packs are installed
- Check file permissions and paths
- Monitor memory usage when processing large files
- Use streaming output for large documents

## 📚 API Reference

See [API Documentation](https://tikara.readthedocs.io/) for complete details.

### Main Classes

- `Tika`: Primary interface
- `TikaraDetectLanguageResult`: Language detection results
- `TikaraUnpackedItem`: Extracted document information

### Common Parameters

- `output_format`: "txt" or "xhtml"
- `output_stream`: Boolean for stream output
- `max_depth`: Integer for recursive extraction
- `content_type`: Optional MIME type hint

## 📄 License

Apache License 2.0 - See [LICENSE](LICENSE) for details.
