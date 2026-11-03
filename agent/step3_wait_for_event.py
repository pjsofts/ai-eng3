# Step 3 — Wait for the world
# Some problems the agent can't fix: here the payment gateway, run by another
# team, is down. So the agent waits, without holding a process open, until an
# event says the world changed. The event is a doorbell, not the truth: after
# waking up, the agent looks at checkout again before it believes anything.
from datetime import timedelta

import inngest

import checkout
from client import client
from llm import decide
from policy import POLICY

GOAL = "Checkout is healthy again: error rate under 5%."
MAX_CYCLES = 6


@client.create_function(
    fn_id="step3-wait-for-event",
    trigger=inngest.TriggerEvent(event="checkout/alert"),
    retries=3,
    singleton=inngest.Singleton(key="event.data.service", mode="skip"),  # 3 alerts, still ONE run
)
def incident_agent(ctx: inngest.ContextSync) -> str:
    notes = []
    for cycle in range(1, MAX_CYCLES + 1):
        state = ctx.step.run(f"observe-{cycle}", checkout.read_state)
        if goal_met(state):
            return f"Fixed: checkout is healthy after {cycle - 1} actions."

        choice = ctx.step.run(f"decide-{cycle}", decide, GOAL, state, notes)
        action = choice["action"]
        kind = POLICY[action]

        if kind == "wait":
            event = ctx.step.wait_for_event(f"wait-{cycle}", event="checkout/recovered",
                                            timeout=timedelta(minutes=2))
            notes.append("wait: " + ("woke up, checkout/recovered arrived" if event else "timed out"))
            continue                  # either way, look again: never trust the doorbell alone

        if kind not in ("read", "write"):
            return f"Stopped: '{action}' needs something this agent can't do yet."

        result = ctx.step.run(f"act-{cycle}", checkout.run_tool, action)
        notes.append(f"{action}: {result}")
        if kind == "write":
            ctx.step.sleep(f"settle-{cycle}", timedelta(seconds=10))

    return f"Gave up after {MAX_CYCLES} cycles. A person needs to look."


def goal_met(state):
    return state["error_rate"] < 5
