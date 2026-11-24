# Step 2 — Durable steps
# The same loop, but every piece of work is a named step: ctx.step.run(id, fn).
# Inngest saves each step's result. If the process dies, Inngest runs the
# function again from the top, and every finished step hands back its saved
# result instead of running again. No model call is paid for twice.
from datetime import timedelta

import inngest

import checkout
from client import client
from llm import decide
from policy import POLICY

GOAL = "Checkout is healthy again: error rate under 5%."
MAX_CYCLES = 6


@client.create_function(fn_id="step2-durable-steps", trigger=inngest.TriggerEvent(event="checkout/alert"),
                        retries=3)
def incident_agent(ctx: inngest.ContextSync) -> str:
    notes = []
    for cycle in range(1, MAX_CYCLES + 1):
        # The cycle number makes every step id unique: "observe-1", "observe-2", ...
        state = ctx.step.run(f"observe-{cycle}", checkout.read_state)
        if goal_met(state):
            return f"Fixed: checkout is healthy after {cycle - 1} actions."

        choice = ctx.step.run(f"decide-{cycle}", decide, GOAL, state, notes)
        action = choice["action"]
        if POLICY[action] not in ("read", "write"):
            return f"Stopped: '{action}' needs something this agent can't do yet."

        result = ctx.step.run(f"act-{cycle}", checkout.run_tool, action)
        notes.append(f"{action}: {result}")

        if POLICY[action] == "write":
            # Give the metrics time to catch up. Inngest holds this timer,
            # so our process can even die while it sleeps.
            ctx.step.sleep(f"settle-{cycle}", timedelta(seconds=10))

    return f"Gave up after {MAX_CYCLES} cycles. A person needs to look."


def goal_met(state):
    return state["error_rate"] < 5
