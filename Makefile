.PHONY: simulate report test lint verify clean

simulate:
	python3 -m app.cli simulate

report:
	python3 -m app.cli report

test:
	pytest -q

lint:
	ruff check app tests

verify: lint test report

clean:
	rm -rf generated

