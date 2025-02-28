.PHONY: all init clean lint check fix

SHELL := /bin/bash

CMD:=poetry run
PYTHONPATH=$(PWD)
# For development hosts w/o desktop GUI
COVERAGE_EXPORT="$(PWD)/.coverage"

all: lint fix

init:
	poetry install

lint:
	$(CMD) pylint viewmaster --ignore migrations --disable=no-member

check:
	$(CMD) black viewmaster --check

fix:
	$(CMD) black viewmaster

clean:
	git clean -Xdf   # Delete all files in .gitignore
