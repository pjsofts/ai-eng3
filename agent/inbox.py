# inbox.py — where the agent asks a person, and the person answers.
#
# One JSON file of requests. The agent writes a request; a person reads it
# (world.py or the visualizer) and answers. The answer then reaches the
# sleeping agent as an Inngest event called "inbox/answered".
import json
import os

INBOX_FILE = os.path.join(os.path.dirname(__file__), "..", ".data", "inbox.json")


def ask(run_id, kind, text):
    """kind is "approval" (yes / no) or "help" (a written answer)."""
    requests = load()
    request_id = f"req-{len(requests) + 1}"
    requests[request_id] = {"run_id": run_id, "kind": kind, "text": text, "answer": None}
    save(requests)
    return request_id


def answer(request_id, approved, reply=""):
    """Record the person's answer. Returns the event to send to the agent."""
    requests = load()
    requests[request_id]["answer"] = {"approved": approved, "reply": reply}
    save(requests)
    return {"name": "inbox/answered",
            "data": {"request_id": request_id, "approved": approved, "reply": reply}}


def pending():
    return {rid: r for rid, r in load().items() if r["answer"] is None}


def clear():
    save({})


def load():
    if not os.path.exists(INBOX_FILE):
        return {}
    with open(INBOX_FILE) as file:
        return json.load(file)


def save(requests):
    os.makedirs(os.path.dirname(INBOX_FILE), exist_ok=True)
    with open(INBOX_FILE, "w") as file:
        json.dump(requests, file, indent=1)
