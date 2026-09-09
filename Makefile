.PHONY: test install doctor package

test:
	python3 -m unittest discover -s tests -v
	/bin/zsh -n scripts/launch.zsh

install:
	python3 install.py

doctor:
	python3 install.py doctor

package:
	mkdir -p dist
	git archive --format=zip --prefix=iterm2-status/ --output=dist/iterm2-status.zip HEAD
