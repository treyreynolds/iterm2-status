.PHONY: test install doctor package

test:
	python3 -B tools/dev.py validate
	python3 -B -m unittest discover -s tests -v
	/bin/zsh -n scripts/launch.zsh

install:
	python3 install.py

doctor:
	python3 install.py doctor

package:
	python3 -B tools/dev.py package
