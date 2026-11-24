# Step 1 — A goal and a loop
# An alert wakes the agent up, but the alert is not the truth. Every cycle the
# agent LOOKS at checkout, the model picks ONE action, and the code runs it.
# The code, not the model, decides when the goal is met.
import inngest

import checkout
from client import client
from llm import decide
from policy import POLICY

GOAL = "Checkout is healthy again: error rate under 5%."
MAX_CYCLES = 6


@client.create_function(fn_id="step1-goal-loop", trigger=inngest.TriggerEvent(event="checkout/alert"))
def incident_agent(ctx: inngest.ContextSync) -> str:
    notes = []                                     # what happened so far, for the model
    for cycle in range(1, MAX_CYCLES + 1):
        state = checkout.read_state()              # observe: a fresh read, every cycle
        if goal_met(state):
            return f"Fixed: checkout is healthy after {cycle - 1} actions."

        choice = decide(GOAL, state, notes)        # the model proposes ONE action
        action = choice["action"]
        if POLICY[action] not in ("read", "write"):
            return f"Stopped: '{action}' needs something this agent can't do yet."

        result = checkout.run_tool(action)         # the code runs it
        notes.append(f"{action}: {result}")

    return f"Gave up after {MAX_CYCLES} cycles. A person needs to look."


def goal_met(state):
    # Checked in code, against fresh facts. The model does not mark its own homework.
    return state["error_rate"] < 5
