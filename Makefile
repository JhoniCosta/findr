.PHONY: run test install uninstall clean

run:
	FINDR_LOG=INFO ./bin/findr

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

install:
	./install.sh

uninstall:
	./uninstall.sh

clean:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
