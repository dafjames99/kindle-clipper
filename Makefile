CONFIG      ?= config.yaml
PLIST_SRC   := $(PWD)/com.kindleclipper.watch.plist
PLIST_DEST  := $(HOME)/Library/LaunchAgents/com.kindleclipper.watch.plist
LABEL       := com.kindleclipper.watch

.PHONY: run dry-run watch watch-dry install-service uninstall-service service-logs cleanup

run:
	uv run python -m kindle_clipper.cli --config $(CONFIG)

dry-run:
	uv run python -m kindle_clipper.cli --config $(CONFIG) --dry-run

watch:
	uv run python -m kindle_clipper.watch --config $(CONFIG)

watch-dry:
	uv run python -m kindle_clipper.watch --config $(CONFIG) --dry-run

install-service:
	cp $(PLIST_SRC) $(PLIST_DEST)
	launchctl bootstrap gui/$$(id -u) $(PLIST_DEST)
	@echo "Service loaded. Logs: ~/Library/Logs/kindleclipper.log"

uninstall-service:
	launchctl bootout gui/$$(id -u) $(PLIST_DEST)
	rm -f $(PLIST_DEST)
	@echo "Service removed."

service-logs:
	tail -f ~/Library/Logs/kindleclipper.log

cleanup:
	uv run python scripts/cleanup.py