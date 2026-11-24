"""Build the replay-only version of the UI as static files (for GitHub Pages).

Each workflow runs once in replay mode at normal speed; its event stream is
saved with timestamps, and the page plays it back without a server.

    python export_static.py ../pjsofts.github.io/public/webinar/ai-agent-workflows/demo
"""
import json
import shutil
import sys
from pathlib import Path

import server

target = Path(sys.argv[1])
target.mkdir(parents=True, exist_ok=True)

data = server.describe()
data.pop("base_url")
data["recordings"] = {}
for workflow in data["workflows"]:
    name = workflow["name"]
    run = server.Run(name, workflow["example"], "replay", False, "normal")
    server.CURRENT = run
    run.execute()
    server.CURRENT = None
    events = []
    while not run.events.empty():
        events.append(run.events.get())
    assert any(e["type"] == "done" for e in events), f"{name} did not finish"
    data["recordings"][name] = events
    print(f"{name}: {len(events)} events, {events[-1]['t']:.1f}s")

(target / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
for name in ("app.js", "style.css"):
    shutil.copy(server.UI / name, target / name)
page = (server.UI / "index.html").read_text()
page = page.replace('<script src="app.js', '<script>window.STATIC = true</script>\n  <script src="app.js')
(target / "index.html").write_text(page)
print(f"wrote {target}")
