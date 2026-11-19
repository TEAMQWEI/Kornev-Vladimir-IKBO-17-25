.PHONY: run test

run:
	python -m src.main --config config.ini

test:
	python -m unittest discover -s tests -v