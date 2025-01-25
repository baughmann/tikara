stubs:
	@uv run python -m stubgenj --classpath "src/tikara/jars/tika-app-3.0.0.jar" --convert-strings org.apache.tika java org.apache.commons org.w3c.dom org.xml.sax --output-dir stubs --no-stubs-suffix
# no idea why it generates stubs for jpype, but we have to remove them
	@rm -rf stubs/jpype-stubs

ruff:
	@uv run ruff check . --fix && ruff format

test:
	@uv run python -m pytest -vv -s

test_coverage:
	@uv run python -m pytest --junitxml=resources/junit/junit.xml --html=resources/junit/report.html  --cov-report term --cov-report xml:resources/coverage.xml --cov=tikara

safety:
	@uv run safety scan --save-as html resources/safety_scan.html

badges:
	@genbadge coverage -i resources/coverage.xml -o resources/images/coverage.svg
	@genbadge tests -i resources/junit/junit.xml -o resources/images/tests.svg

docs:
	@uv run sphinx-apidoc -f -o docs/source/ .
	@uv run sphinx-build -b html docs/source/ docs/build/html

prepush: ruff test test_coverage safety badges

.PHONY: stubs ruff test test_coverage safety badges docs prepush