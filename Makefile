.PHONY: demo fixtures test check

demo:
	./demo.sh

fixtures:
	python3 scripts/generate_fixtures.py

test: fixtures
	python3 -m unittest discover -s tests -v

check: fixtures
	python3 -m compileall -q krishi_vani tests scripts
	python3 -m unittest discover -s tests -v
