# checkout.py — the service our agent looks after.
#
# A pretend checkout service for an online shop. Its whole state is one JSON
# file, so it stays exactly as it was when the agent process crashes.
#
#   read_state()                    what the agent observes every cycle
#   run_tool(name, action_id)       the only way to look closer or change it
#
# The rest is for the people running the demo (world.py and the visualizer):
#   start_incident(fault)   break it in one of three ways
#   fix_gateway()           the payment team fixes THEIR service, not ours
#   someone_deploys()       another engineer changes checkout while we wait
import json
import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", ".data", "checkout.json")

LOGS = {
    "feature": "ERROR express_checkout: crash in confirm_payment() for 42% of orders",
    "release": "ERROR payments failing for 42% of orders since the 14:02 deploy",
    "dependency": "ERROR payment gateway timed out after 30s (gateway is run by the payments team)",
}


# ---- what the agent can see and do ------------------------------------------

def read_state():
    """The facts, read fresh: never trust what an alert said a minute ago."""
    state = load()
    return {
        "version": state["version"],
        "error_rate": error_rate(state),
        "status": "healthy" if error_rate(state) < 5 else "failing",
    }


def run_tool(name, action_id=None):
    if name == "read_logs":
        return "\n".join(load()["logs"][-5:])
    if name == "read_changes":
        return "\n".join(load()["changes"][-5:])
    return change_service(name, action_id)


def change_service(name, action_id=None):
    state = load()

    # Same action_id as before? Then this is a retry of something we already did:
    # send back the same answer and do NOT do it a second time.
    if action_id in state["done"]:
        return state["done"][action_id]

    if name == "disable_feature":
        state["express_checkout"] = False
        state["changes"].append("Turned off the express checkout feature")
    elif name == "rollback_release":
        state["release"] = "v1"
        state["changes"].append("Rolled checkout back to release v1")
    else:
        raise ValueError(f"checkout has no action called {name}")

    state["version"] += 1
    result = f"{name} done. Error rate is now {error_rate(state)}%."
    if action_id:
        state["done"][action_id] = result

    lose_reply = state["lose_next_reply"]
    state["lose_next_reply"] = False
    save(state)

    if lose_reply:
        # The change happened, but the answer never reached the agent.
        raise ConnectionError("The network dropped the reply (the change WAS made).")
    return result


def error_rate(state):
    broken = state["express_checkout"] or state["release"] == "v2" or not state["gateway_ok"]
    return 42 if broken else 1


# ---- for the demo: the world outside the agent -------------------------------

def start_incident(fault, lose_next_reply=False):
    changes = ["Deployed checkout release v1 (last week)"]
    if fault == "feature":
        changes.append("Turned on the express checkout feature")
    if fault == "release":
        changes.append("Deployed checkout release v2 at 14:02")
    save({
        "version": 1,
        "release": "v2" if fault == "release" else "v1",
        "express_checkout": fault == "feature",
        "gateway_ok": fault != "dependency",
        "logs": [LOGS[fault]],
        "changes": changes,
        "done": {},          # action_id -> result: what the service already did
        "lose_next_reply": lose_next_reply,
    })


def fix_gateway():
    state = load()
    state["gateway_ok"] = True
    state["version"] += 1
    state["logs"].append("INFO payment gateway is answering again (fixed by the payments team)")
    save(state)


def someone_deploys():
    state = load()
    state["version"] += 1
    state["changes"].append("Another engineer changed the checkout config")
    save(state)


def load():
    with open(STATE_FILE) as file:
        return json.load(file)


def save(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as file:
        json.dump(state, file, indent=1)
