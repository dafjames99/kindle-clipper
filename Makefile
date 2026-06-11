CONFIG ?= config.yaml

.PHONY: run dry-run cleanup

run:
	uv run python -m kindle_clipper.cli --config $(CONFIG)

dry-run:
	uv run python -m kindle_clipper.cli --config $(CONFIG) --dry-run

cleanup:
	uv run python scripts/cleanup.py