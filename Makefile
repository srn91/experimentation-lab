.PHONY: simulate report test lint verify clean serve

simulate:
	python3 -m app.cli simulate

report:
	python3 -m app.cli report

test:
	pytest -q

lint:
	ruff check app tests

verify: lint test report

serve:
	python3 -m uvicorn app.web:app --host 0.0.0.0 --port $${PORT:-8000}

clean:
	rm -rf generated
