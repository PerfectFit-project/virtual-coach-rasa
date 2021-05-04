.PHONY: clean clean-build clean-pyc clean-test release dist

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '*_cache' -exec rm -fr {} +

clean-test:
	rm -f .coverage
	rm -f coverage.xml tests/coverage.xml
	rm -fr htmlcov  tests/htmlcov

dist: clean
	python setup.py sdist bdist_wheel
	ls -l dist

install-dist:
	pip install `ls dist/*.gz`"[tests]"

release:
	python -m twine upload dist/*
