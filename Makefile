documentation:
	jb clean docs
	jb build docs

install:
	pip install -e .

format:
	black . -l 79
