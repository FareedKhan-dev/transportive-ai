"""loop/journal.py: each stage once, and a crash resumes."""
import json
from pathlib import Path


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = self.path.read_text(encoding="utf-8").splitlines() if self.path.exists() else []
        self.done = {row["key"]: row["out"] for row in map(json.loads, lines)}

    def once(self, key, stage):
        # run once, save, return the saved copy
        if key not in self.done:
            line = json.dumps({"key": key, "out": stage()})
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            self.done[key] = json.loads(line)["out"]
        return self.done[key]
