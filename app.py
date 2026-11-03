"""The real thing: serve one step to the Inngest Dev Server.

    npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest   # terminal 1 → http://127.0.0.1:8288
    python app.py 2                                                    # terminal 2: serve step 2
    python world.py alert feature                                      # terminal 3: break checkout

Durability drill: Ctrl-C terminal 2 while the run sleeps, start it again, and
watch the run continue from its last finished step in the Inngest dashboard.
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "agent"))

import inngest.fast_api  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from client import client  # noqa: E402

STEPS = {
    "1": "step1_goal_loop",
    "2": "step2_durable_steps",
    "3": "step3_wait_for_event",
    "4": "step4_human_approval",
    "5": "step5_safe_retries",
    "6": "step6_ask_for_help",
}

number = sys.argv[1] if len(sys.argv) > 1 else "6"
step = importlib.import_module(STEPS[number])

app = FastAPI()
inngest.fast_api.serve(app, client, [step.incident_agent])   # only one step at a time: they share a trigger

if __name__ == "__main__":
    print(f"Serving {STEPS[number]} at http://127.0.0.1:8000/api/inngest")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
