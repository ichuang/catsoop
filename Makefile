install:
	pip3 install .

develop:
	pip3 install -e .

uninstall:
	pip3 uninstall -y catsoop

test:
	pytest catsoop/test

deb:
	dpkg-buildpackage -us -uc -b

.PHONY: install develop test uninstall
