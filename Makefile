PROJECT=dolead_entry_points
RUN=poetry run

install:
	poetry update

test:
	$(RUN) pytest --cov=$(PROJECT)

pep8:
	$(RUN) pycodestyle --ignore=E126,E127,E128,W503 $(PROJECT)/

mypy:
	$(RUN) mypy $(PROJECT) --ignore-missing-imports

lint: pep8 mypy

clean:
	rm -rf build dist .coverage tests_coverage/ .mypy_cache .pytest_cache \
		$(PROJECT)/*.cover
