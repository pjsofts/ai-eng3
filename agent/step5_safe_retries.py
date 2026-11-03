# Step 5 — Safe retries
# Checkout makes the change, then the reply gets lost. Inngest retries the
# step. Did the change happen? With a random id the service can't tell, and
# does it twice. With an id built from the run, the cycle and the action, the
# retry is recognised as the same intent: checkout answers "already done".
from datetime import timedelta

import inngest

import checkout
import inbox
from client import client
from llm import decide
from policy import POLICY

GOAL = "Checkout is healthy again: error rate under 5%."
MAX_CYCLES = 6


@client.create_function(fn_id="step5-safe-retries", trigger=inngest.TriggerEvent(event="checkout/alert"),
                        retries=3, singleton=inngest.Singleton(key="event.data.service", mode="skip"))
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
            continue

        if kind == "approval":
            question = f"May I run {action} on checkout version {state['version']}? {choice['reason']}"
            answer = ask_person(ctx, cycle, "approval", question)
            if answer is None:
                return "Stopped: nobody answered. Silence is not a yes."
            if not answer["approved"]:
                return f"Stopped: a person said no to {action}."

            fresh = ctx.step.run(f"recheck-{cycle}", checkout.read_state)
            if fresh["version"] != state["version"]:
                notes.append(f"{action} was approved, but checkout changed while we waited. Approval dropped.")
                continue              # look again, decide again, ask again

        elif kind not in ("read", "write"):
            return f"Stopped: '{action}' needs something this agent can't do yet."

        # Same run + same cycle + same action = same intent = same id, on every retry
        # and after every crash. A random id (uuid4()) would look new each time.
        action_id = f"{ctx.run_id}:{cycle}:{action}"
        result = ctx.step.run(f"act-{cycle}", checkout.run_tool, action, action_id)
        notes.append(f"{action}: {result}")
        if kind != "read":
            ctx.step.sleep(f"settle-{cycle}", timedelta(seconds=10))

    return f"Gave up after {MAX_CYCLES} cycles. A person needs to look."


def ask_person(ctx, cycle, kind, text):
    """Write the question to the inbox, then sleep until THIS request is answered."""
    request_id = ctx.step.run(f"ask-{cycle}", inbox.ask, ctx.run_id, kind, text)
    event = ctx.step.wait_for_event(
        f"answer-{cycle}",
        event="inbox/answered",
        if_exp=f"async.data.request_id == '{request_id}'",
        timeout=timedelta(minutes=10),
    )
    return event.data if event else None


def goal_met(state):
    return state["error_rate"] < 5
