# Step 6 — Make the eval honest
# Two fixes for the one lie step 5 found:
#   1. the schema uses the names Excalidraw reads: label, and start / end
#      (schemas.ADD_SKELETON, prompts.SKELETON)
#   2. the eval's add_elements runs draw(), exactly like the app
#      (tools.add_elements), so the scorers read what the user sees
# Compare with step 4. Maybe the same digits, but now they mean something.
from agent import run_agent
from evals import called_tools, compare, load_dataset, load_experiment, run_eval
from prompts import SKELETON
from step4_tools import SCORERS
from tools import CANVAS, add_elements, new_canvas, query_canvas, remove_elements, update_elements

TOOLS = [query_canvas, add_elements, update_elements, remove_elements]


def run(dataset):
    experiment = run_eval("step6_honest", load_dataset(dataset), task, SCORERS)
    return compare(load_experiment("step4_tools"), experiment)


def task(case):
    seed = case.get("seed", {})
    new_canvas(seed.get("elements", []))
    messages = [
        {"role": "system", "content": SKELETON},
        {"role": "user", "content": case["input"]},
    ]
    answer = run_agent(messages, TOOLS)
    return {"text": answer, "elements": list(CANVAS), "tool_calls": called_tools(messages)}


if __name__ == "__main__":
    print(run("golden.json"))
