stubs:
	@uv run python -m stubgenj --classpath "src/tikara/jars/tika-app-3.0.0.jar" --convert-strings org.apache.tika java org.apache.commons org.w3c.dom org.xml.sax javax.xml javax.accessibility javax.crypto org.apache.poi --output-dir stubs --no-stubs-suffix
# no idea why it generates stubs for jpype, but we have to remove them
	@rm -rf stubs/jpype-stubs

ruff:
	@uv run ruff check . --fix && ruff format

test:
	@uv run python -m pytest -vv -s

test_coverage:
	@uv run python -m pytest --junitxml=junit.xml  --cov-report term --cov-report xml:coverage.xml --cov=tikara

safety:
	@uv run safety scan --save-as html --output safety.html

docs:
	@uv run pydocstyle src
	@uv run sphinx-apidoc -f -o docs/source/ . "test*"
	@uv run sphinx-build -b html docs/source/ docs/build/html


prepush: ruff test_coverage safety --save-as html --output safety.html

.PHONY: stubs ruff test test_coverage safety docs prepush