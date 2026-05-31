.PHONY: test test-cov lint clean

test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=term-missing -v

lint:
	ruff check app

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache