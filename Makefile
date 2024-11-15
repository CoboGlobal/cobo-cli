install:
	poetry install
	pre-commit install

pre-commit:
	pre-commit run --all-files
