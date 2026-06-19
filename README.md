# Summary
As someone who reads a lot, I'd much prefer to do so either from a real book, or alternatively on a Kindle device. 

There's a lot of content online that I want to read, but must do so on a computer/phone screen.

This project gets content (e.g. Blogs, Essays^[As well as journals & papers, pending `.pdf` compatibility]) straight **from google chrome to my kindle**, in clean `EPUB` format.

## What about the Kindle Chrome extension?
This does exist, but is inadequate for me personally because:
- I *already* use Obsidian (& the associated web clipper extension)
- It's more prone to error & is less flexible than Obsidian web clipper.

This script is easy enough for me & I can set up a *CRON* / folder-watcher to handle the job for specific subsets of my Obsidian clippings.

# Setup

Clone this repository first of all.

## Environment
### System dependencies
Install these before anything else:
- [**Pandoc**](https://pandoc.org/installing.html) — the EPUB converter
- [**uv**](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager

On macOS both are available via Homebrew:
```bash
brew install pandoc uv
```

### Python dependencies
```bash
uv sync
```
then run, one by one:
```bash
cp example-state.json state.json
cp config.example.yaml config.ymal
```
Configure the settings in `config.yaml` to suit your preferences - the `Obsidian_dir` + `clippings_subdir` *can* point to any directory where you store `.md` files you want on your kindle.

There will be information in the `config.yaml` file for setting up the non-code aspects - e.g. setting up Kindle email & accessing the Gmail app password for your app.

## (Recommended) Obsidian Chrome Extension
For getting webpages into markdown form, the best option is to use the [Obsidian Web Clipper extension for chrome](https://chromewebstore.google.com/detail/obsidian-web-clipper/), create a template & set the output dir to that as in your `config.yaml`

Though this does require having the [**Obsidian**](https://obsidian.md/) app installed, I would recommend using this app regardless - it's a great lightweight environment for storing & managing markdown notes/files, with a bunch of great features.

**Otherwise**, if you don't want to follow the obsidian route, the idea of `Obsidian_dir` + `clippings_subdir` in the config is to locate **markdown files**^[Also eventually, `pdf` & other files.] that you would like to convert to EPUB & sent to kindle. Any such directory will do. 


# Running
## Makefile
I like using makefiles for repetitive bash procedures. The `Makefile` simplifies bash scripts:
```bash
make run          # convert and send
make dry-run      # convert only, no email
make watch        # folder-watcher (see below)
make cleanup
```

## Direct
### Full
Full run (from root directory):
```bash
uv run python -m kindle_clipper.cli --config config.yaml
```

### Dry-run
Or only for converting (i.e. no email sending):
```bash
uv run python -m kindle_clipper.cli --config config.yaml --dry-run
```

The `state.json` file will keep track of what files have been processed to avoid duplicating conversions.

### Cleanup
If you don't want to store the EPUBs locally, or if you've previously ran --dry-run and want to redo the run **fully**, use `scripts/cleanup.py` to automate:
1. Wipe `state.json` clean
2. Erase contents of `output_dir`
```bash
uv run python scripts/cleanup.py
```

## Folder-watcher (recommended)
Rather than running the script manually, you can run a persistent watcher that processes new clippings as soon as they appear in the folder.

### One-off
```bash
make watch        # watch and send
make watch-dry    # watch, convert only
```

### Background service via launchd (macOS)
To have the watcher start automatically on login and restart if it ever crashes, register it as a LaunchAgent:

1. Copy and fill in the plist template:
```bash
cp com.kindleclipper.watch.plist.example com.kindleclipper.watch.plist
```
Edit `com.kindleclipper.watch.plist` and replace the three placeholder paths:
- `/path/to/uv` → output of `which uv`
- `/path/to/kindle-clipper` → output of `pwd` from the project root
- `/Users/yourname/` → your actual home directory

2. Install and start the service:
```bash
make install-service
```

3. Check it's running and tail the log:
```bash
launchctl print gui/$(id -u)/com.kindleclipper.watch
make service-logs
```

To stop and remove the service:
```bash
make uninstall-service
```
