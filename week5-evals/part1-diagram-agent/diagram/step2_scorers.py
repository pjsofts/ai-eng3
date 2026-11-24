# Step 2 — Automated scorers
# Scoring by hand doesn't scale. A scorer is a small function that grades
# every run the same way, in milliseconds. run_eval runs the dataset, scores
# every case and saves the experiment: this is the baseline the next steps beat.
#
# A modify case ("make the login box red") needs a diagram to modify. So
# build_messages fakes the conversation that drew it: the agent should not be
# able to tell it apart from a session it lived through.
import json

from agent import run_agent
from evals import called_tools, load_dataset, report, run_eval
from prompts import FIRST
from scorers import label_keywords, preservation, schema, structure
from step0_first_agent import TOOLS
from tools import CANVAS, new_canvas

SCORERS = [schema, structure, preservation, label_keywords]


def run(dataset):
    experiment = run_eval("step2_baseline", load_dataset(dataset), task, SCORERS)
    return report(experiment)


def task(case):
    """One run of the agent, the same as in the app. Returns what the scorers read."""
    seed = case.get("seed", {})
    new_canvas(seed.get("elements", []))
    messages = [{"role": "system", "content": FIRST}] + build_messages(case)
    answer = run_agent(messages, TOOLS)
    return {"text": answer, "elements": list(CANVAS), "tool_calls": called_tools(messages)}


def build_messages(case):
    """A create case is one user message. A modify case starts mid-conversation."""
    if "seed" not in case:
        return [{"role": "user", "content": case["input"]}]
    seed = case["seed"]
    drew = {"id": "seed", "type": "function", "function": {
        "name": "generate_diagram", "arguments": json.dumps({"elements": seed["elements"]})}}
    return [
        {"role": "user", "content": seed["request"]},
        {"role": "assistant", "content": "", "tool_calls": [drew]},
        {"role": "tool", "tool_call_id": "seed", "content": f"Drew {len(seed['elements'])} elements."},
        {"role": "assistant", "content": seed["reply"]},
        {"role": "user", "content": case["input"]},
    ]


if __name__ == "__main__":
    print(run("golden.json"))
