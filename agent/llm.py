# llm.py — the only code that talks to the model.
#
#   decide(goal, state, notes) -> {"action": ..., "reason": ..., "question": ...}
#
# The model picks ONE next action. It never runs anything itself.
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from policy import POLICY

load_dotenv()
client = OpenAI()   # reads OPENAI_API_KEY and OPENAI_BASE_URL from .env
MODEL = os.environ.get("MODEL", "gpt-4o-mini")

SYSTEM = """You are an on-call agent for an online shop's checkout service.
Each turn, pick exactly ONE next action:
  read_logs         see the latest error logs
  read_changes      see recent deploys and config changes
  disable_feature   turn off the express checkout feature
  rollback_release  roll checkout back to the previous release
  ask_human         ask the on-call engineer a question (write it in "question")
  wait              nothing safe to do now: wait until the service changes
Look before you change anything. If the cause is outside our service, do not
invent a fix: ask a human or wait.
Reply with JSON only: {"action": "...", "reason": "one short sentence", "question": ""}"""


def decide(goal, state, notes):
    prompt = (f"Goal: {goal}\n\n"
              f"Checkout right now: {json.dumps(state)}\n\n"
              f"What happened so far:\n" + ("\n".join(notes) or "(nothing yet)"))
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    choice = json.loads(response.choices[0].message.content)

    if choice.get("action") not in POLICY:      # never trust the model's output blindly
        return {"action": "wait", "reason": f"the model asked for an unknown action: {choice}", "question": ""}
    return choice
