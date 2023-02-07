install:
	poetry update

clean:
	rm -rf build dist

build: clean
	poetry check
	poetry build

deploy: build
	poetry publish
	git tag $(shell poetry version -s)
	git push --tags
