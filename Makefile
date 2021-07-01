PROJECT=dolead_entry_points
RUN=

test:
	pytest --cov=$(PROJECT)

pep8:
	pycodestyle --ignore=E126,E127,E128,W503 $(PROJECT)/

mypy:
	mypy $(PROJECT) --ignore-missing-imports

lint: pep8 mypy

clean:
	rm -rf build dist .coverage tests_coverage/ .mypy_cache .pytest_cache \
		$(PROJECT)/*.cover
