# scripts/cleanup.py
from pathlib import Path
import shutil
import yaml

config = yaml.safe_load(Path("config.yaml").read_text())

output_dir = Path(config["output_dir"]).expanduser()
state_file = Path(config["state_file"])

if output_dir.exists():
    shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
state_file.unlink(missing_ok=True)